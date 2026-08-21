import asyncio

from langchain_core.messages import HumanMessage

from Backend.Graph.builder import graph


async def main():
    state = {
        "messages": [
            HumanMessage(
                content="Plan a 5 day trip to Tokyo under ₹2 lakh."
            )
        ]
    }

    result = await graph.ainvoke(state)

    print(result)


if __name__ == "__main__":
    asyncio.run(main())