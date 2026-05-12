from agents import function_tool
from infrastructure.logging.logger import logger
from repositories.after_sales_repository import (
    query_order_by_id,
    query_repair_by_id,
    query_warranty_by_product,
)


@function_tool
async def query_order_status(order_id: str) -> str:
    """
    查询订单状态和物流信息。

    Args:
        order_id: 订单编号，如 ORD20240512001

    Returns:
        订单状态信息，包含商品名称、物流状态、预计送达时间
    """
    logger.info(f"[AfterSales] 查询订单状态: {order_id}")
    order = query_order_by_id(order_id)
    if order:
        return (
            f"订单 {order['order_id']} 状态：\n"
            f"- 商品：{order['product']}\n"
            f"- 状态：{order['status']}\n"
            f"- 物流：{order['logistics']}\n"
            f"- 预计送达：{order['estimated_delivery']}\n"
            f"- 下单日期：{order['purchase_date']}"
        )
    return f"未找到订单号 {order_id}，请确认订单号是否正确。订单号格式通常为 ORD 开头，如 ORD20240512001。"


@function_tool
async def query_warranty_info(product: str) -> str:
    """
    查询产品的保修信息和保修状态。

    Args:
        product: 产品名称或型号，如 ThinkPad X1 Carbon

    Returns:
        保修信息，包含购买日期、保修到期日、保修类型、当前状态
    """
    logger.info(f"[AfterSales] 查询保修信息: {product}")
    warranty = query_warranty_by_product(product)
    if warranty:
        return (
            f"{warranty['product']} 保修信息：\n"
            f"- 购买日期：{warranty['purchase_date']}\n"
            f"- 保修到期：{warranty['warranty_end']}\n"
            f"- 保修类型：{warranty['warranty_type']}\n"
            f"- 当前状态：{warranty['status']}"
        )
    return f"未找到产品「{product}」的保修信息，请确认产品型号是否正确。"


@function_tool
async def query_repair_progress(repair_id: str) -> str:
    """
    查询维修工单的进度和状态。

    Args:
        repair_id: 维修工单号，如 RPR20240501

    Returns:
        维修进度信息，包含设备型号、故障描述、当前状态、预计完成时间、工程师备注
    """
    logger.info(f"[AfterSales] 查询维修进度: {repair_id}")
    repair = query_repair_by_id(repair_id)
    if repair:
        return (
            f"维修工单 {repair['repair_id']} 进度：\n"
            f"- 设备：{repair['product']}\n"
            f"- 故障：{repair['issue']}\n"
            f"- 当前状态：{repair['status']}\n"
            f"- 送修日期：{repair['received_date']}\n"
            f"- 预计完成：{repair['estimated_completion']}\n"
            f"- 工程师备注：{repair['technician_note']}"
        )
    return f"未找到维修工单 {repair_id}，请确认工单号是否正确。工单号格式通常为 RPR 开头，如 RPR20240501。"
