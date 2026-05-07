from agents import function_tool, Runner, handoff
from agents.run import RunConfig
from langfuse import observe

from multi_agent.technical_agent import technical_agent
from multi_agent.service_agent import comprehensive_service_agent
from multi_agent.after_sales_agent import after_sales_agent
from infrastructure.tools.mcp.mcp_servers import search_mcp_client, baidu_mcp_client

from infrastructure.logging.logger import logger


# 1. 定义技术专家智能体工具
@function_tool
@observe(as_type="tool", name="consult_technical_expert")
async def consult_technical_expert(
        query: str,
) -> str:
    """
    【咨询与技术专家】处理技术咨询、设备故障、维修建议以及实时资讯（如股价、新闻、天气）。
    当用户询问：
    1. "怎么修"、"为什么坏了"、"如何操作"等技术问题。
    2. "今天股价"、"现在天气"等实时信息。
    请调用此工具。

    Args:
    query: 用户的原始问题或完整指令。
    """
    try:
        logger.info(f"[Route] 转交技术专家: {query[:30]}...")

        # 直接透传用户指令，不要做任何加工
        result = await Runner.run(
            technical_agent,
            input=query,
            run_config=RunConfig(tracing_disabled=True)
        )
        return result.final_output
    except Exception as e:
        return f"技术专家暂时无法回答: {str(e)}"


# 2. 定义全能业务智能体工具
@function_tool
@observe(as_type="tool", name="query_service_station_and_navigate")
async def query_service_station_and_navigate(
        query: str,
) -> str:
    """
        【服务站专家】处理线下服务站查询、位置查找和地图导航需求。
        当用户询问：
        1. "附近的维修点"、"找小米之家"（服务站查询）。
        2. "怎么去XX"、"导航到XX"（路径规划）。
        3. 任何涉及地理位置和线下门店的请求。
        请调用此工具。
        Args:
            query: 用户的原始问题（包含隐含的位置信息）。
    """
    try:
        logger.info(f"[Route] 转交业务专家: {query[:30]}...")
        result = await Runner.run(
            comprehensive_service_agent,
            input=query,
            run_config=RunConfig(tracing_disabled=True)
        )
        return result.final_output
    except Exception as e:
        return f"业务专家暂时无法回答: {str(e)}"


# 3. 定义订单售后智能体工具
@function_tool
@observe(as_type="tool", name="consult_after_sales_expert")
async def consult_after_sales_expert(
        query: str,
) -> str:
    """
    【订单售后专家】处理订单状态查询、保修期查询、维修进度查询、退换货政策咨询。
    当用户询问：
    1. "我的订单到哪了"、"订单号XXX的物流信息"（订单查询）。
    2. "我的电脑还在保修期内吗"、"保修多久"（保修查询）。
    3. "我的维修工单进度如何"、"电脑修好了吗"（维修进度）。
    4. "买了7天还能退吗"、"换货流程是什么"（退换货政策）。
    请调用此工具。

    Args:
        query: 用户的原始问题或完整指令。
    """
    try:
        logger.info(f"[Route] 转交售后专家: {query[:30]}...")
        result = await Runner.run(
            after_sales_agent,
            input=query,
            run_config=RunConfig(tracing_disabled=True)
        )
        return result.final_output
    except Exception as e:
        return f"售后专家暂时无法回答: {str(e)}"


# 4. 将三个工具暴露出去
AGENT_TOOLS = [
    consult_technical_expert,
    query_service_station_and_navigate,
    consult_after_sales_expert,
]

# 5. Handoff 目标（供编排器使用）
HANDOFF_TARGETS = [
    technical_agent,
    comprehensive_service_agent,
    after_sales_agent,
]


async def run_technical_tool():
    """测试技术专家工具"""
    print("\n" + "=" * 80)
    print("测试技术专家Agent Tool")
    print("=" * 80)
    await search_mcp_client.connect()

    test_cases = ["今天小米股价多少"]

    for query in test_cases:
        print(f"\n 查询: {query}")
        print("-" * 0)
        result = await consult_technical_expert(query=query)
        print(f"回答: {result}\n")

    await search_mcp_client.cleanup()


async def run_service_tool():
    """测试业务服务工具"""
    print("\n" + "=" * 80)
    print("测试业务服务Agent Tool")
    print("=" * 80)

    await baidu_mcp_client.connect()

    test_cases = [
        # "我想去小米之家修电脑",
        "怎么去颐和园",
    ]

    for query in test_cases:
        print(f"\n查询: {query}")
        print("-" * 80)
        result = await query_service_station_and_navigate(query=query)
        print(f"回答: {result}\n")

    await baidu_mcp_client.cleanup()


async def main():
    # 1. 测试技术智能体工具
    # await run_technical_tool()

    # 2. 测试全能业务智能体工具
    await run_service_tool()
    # print("\n所有测试完成！\n")


# 以下是测试代码，可以独立运行测试每个Agent Tool
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
