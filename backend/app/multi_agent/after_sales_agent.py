from agents import Agent
from infrastructure.ai.openai_client import sub_model
from infrastructure.ai.prompt_loader import load_prompt
from infrastructure.tools.local.after_sales import (
    query_order_status,
    query_warranty_info,
    query_repair_progress,
)

# 订单售后智能体
after_sales_agent = Agent(
    name="after_sales_expert",
    instructions=load_prompt("after_sales_agent"),
    model=sub_model,
    tools=[
        query_order_status,
        query_warranty_info,
        query_repair_progress,
    ],
)
