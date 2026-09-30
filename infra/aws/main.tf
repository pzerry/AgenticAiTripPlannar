terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
provider "aws" {
  region = var.region
  default_tags { tags = { Application = var.name, ManagedBy = "Terraform" } }
}
data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "app" {
  name                 = var.name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}
resource "aws_ecs_cluster" "app" { name = var.name }
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.name}"
  retention_in_days = 30
}
resource "aws_security_group" "alb" {
  name   = "${var.name}-alb"
  vpc_id = var.vpc_id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "tasks" {
  name   = "${var.name}-tasks"
  vpc_id = var.vpc_id
  dynamic "ingress" {
    for_each = [8000, 8501]
    content {
      from_port       = ingress.value
      to_port         = ingress.value
      protocol        = "tcp"
      security_groups = [aws_security_group.alb.id]
    }
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_vpc_security_group_ingress_rule" "database" {
  security_group_id            = var.database_security_group_id
  referenced_security_group_id = aws_security_group.tasks.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
}
resource "aws_lb" "app" {
  name               = var.name
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [aws_security_group.alb.id]
  idle_timeout       = 600
}
resource "aws_lb_target_group" "app" {
  for_each    = { api = 8000, ui = 8501 }
  name        = "${var.name}-${each.key}"
  port        = each.value
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    path                = each.key == "api" ? "/" : "/_stcore/health"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  # Streamlit sessions use WebSockets and in-memory state.
  stickiness {
    type    = "lb_cookie"
    enabled = each.key == "ui"
  }
}
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      status_code  = "404"
    }
  }
}
resource "aws_lb_listener_rule" "app" {
  for_each     = { api = var.api_hostname, ui = var.ui_hostname }
  listener_arn = aws_lb_listener.https.arn
  priority     = each.key == "api" ? 10 : 20
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app[each.key].arn
  }
  condition {
    host_header { values = [each.value] }
  }
}
locals {
  task_trust = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  services = {
    api    = { command = ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"], port = 8000 }
    worker = { command = ["python", "-m", "Backend.Memory.worker"], port = 0 }
    ui     = { command = ["python", "-m", "streamlit", "run", "FrontEnd/app.py", "--server.address=0.0.0.0", "--server.port=8501"], port = 8501 }
  }
  environment = {
    APP_ENV              = "production"
    TRAVEL_AUTH_MODE     = "oidc"
    TRAVEL_OIDC_ISSUER   = var.oidc_issuer
    TRAVEL_OIDC_AUDIENCE = var.oidc_audience
    TRAVEL_OIDC_JWKS_URL = var.oidc_jwks_url
  }
}
resource "aws_iam_role" "execution" {
  for_each           = local.services
  name               = "${var.name}-${each.key}-execution"
  assume_role_policy = local.task_trust
}
resource "aws_iam_role_policy_attachment" "execution" {
  for_each   = local.services
  role       = aws_iam_role.execution[each.key].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
resource "aws_iam_role_policy" "secrets" {
  for_each = toset(["api", "worker"])
  role     = aws_iam_role.execution[each.key].id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = var.runtime_secret_arn }
    ], var.secret_kms_key_arn == null ? [] : [
    { Effect = "Allow", Action = ["kms:Decrypt"], Resource = var.secret_kms_key_arn }
  ]) })
}
resource "aws_iam_role" "task" {
  name               = "${var.name}-task"
  assume_role_policy = local.task_trust
}
resource "aws_ecs_task_definition" "app" {
  for_each                 = local.services
  family                   = "${var.name}-${each.key}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution[each.key].arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name = "app"
    # No task starts with this placeholder. CI registers a digest-pinned revision.
    image        = "${aws_ecr_repository.app.repository_url}:bootstrap"
    essential    = true
    command      = each.value.command
    stopTimeout  = 120
    portMappings = each.value.port == 0 ? [] : [{ containerPort = each.value.port, protocol = "tcp" }]
    environment  = [for key, value in(each.key == "ui" ? { TRAVEL_API_URL = "https://${var.api_hostname}" } : local.environment) : { name = key, value = value }]
    secrets      = each.key == "ui" ? [] : [for key in var.runtime_secret_keys : { name = key, valueFrom = "${var.runtime_secret_arn}:${key}::" }]
    logConfiguration = { logDriver = "awslogs", options = {
      awslogs-group         = aws_cloudwatch_log_group.app.name
      awslogs-region        = var.region
      awslogs-stream-prefix = each.key
    } }
  }])
}
resource "aws_ecs_service" "app" {
  for_each                          = local.services
  name                              = "${var.name}-${each.key}"
  cluster                           = aws_ecs_cluster.app.id
  task_definition                   = aws_ecs_task_definition.app[each.key].arn
  desired_count                     = 0
  launch_type                       = "FARGATE"
  platform_version                  = "1.4.0"
  health_check_grace_period_seconds = each.key == "worker" ? null : 180
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }
  dynamic "load_balancer" {
    for_each = each.key == "worker" ? [] : [each.key]
    content {
      target_group_arn = aws_lb_target_group.app[each.key].arn
      container_name   = "app"
      container_port   = each.value.port
    }
  }
  lifecycle { ignore_changes = [task_definition, desired_count] }
  depends_on = [aws_lb_listener_rule.app, aws_iam_role_policy_attachment.execution, aws_iam_role_policy.secrets]
}
resource "aws_iam_role" "github" {
  name = "${var.name}-github"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Allow"
    Principal = { Federated = var.github_oidc_provider_arn }
    Action    = "sts:AssumeRoleWithWebIdentity"
    Condition = { StringEquals = {
      "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
      "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:environment:${var.github_environment}"
    } }
  }] })
}
resource "aws_iam_role_policy" "github" {
  role = aws_iam_role.github.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken", "ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:DescribeImages"], Resource = aws_ecr_repository.app.arn },
    { Effect = "Allow", Action = ["ecs:DescribeServices", "ecs:UpdateService"], Resource = [for service in aws_ecs_service.app : service.id] },
    { Effect = "Allow", Action = ["ecs:RunTask"], Resource = "arn:aws:ecs:${var.region}:${data.aws_caller_identity.current.account_id}:task-definition/${var.name}-api:*", Condition = { ArnEquals = { "ecs:cluster" = aws_ecs_cluster.app.arn } } },
    { Effect = "Allow", Action = ["ecs:DescribeTasks", "ecs:StopTask"], Resource = "arn:aws:ecs:${var.region}:${data.aws_caller_identity.current.account_id}:task/${aws_ecs_cluster.app.name}/*" },
    { Effect = "Allow", Action = ["iam:PassRole"], Resource = concat([aws_iam_role.task.arn], [for role in aws_iam_role.execution : role.arn]), Condition = { StringEquals = { "iam:PassedToService" = "ecs-tasks.amazonaws.com" } } }
  ] })
}
output "github_variables" {
  value = {
    AWS_REGION          = var.region
    AWS_DEPLOY_ROLE_ARN = aws_iam_role.github.arn
    ECR_REPOSITORY      = aws_ecr_repository.app.repository_url
    ECS_CLUSTER         = aws_ecs_cluster.app.name
    ECS_API_SERVICE     = aws_ecs_service.app["api"].name
    ECS_WORKER_SERVICE  = aws_ecs_service.app["worker"].name
    ECS_UI_SERVICE      = aws_ecs_service.app["ui"].name
    API_HEALTH_URL      = "https://${var.api_hostname}/"
    UI_HEALTH_URL       = "https://${var.ui_hostname}/_stcore/health"
  }
}
output "load_balancer_dns_name" { value = aws_lb.app.dns_name }
