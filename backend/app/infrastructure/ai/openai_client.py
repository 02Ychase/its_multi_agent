from agents import OpenAIChatCompletionsModel
from config.settings import settings
from openai import AsyncOpenAI

# 主模型配置 (MiMo)
MAIN_API_KEY = settings.MAIN_API_KEY
MAIN_BASE_URL = settings.MAIN_BASE_URL
MAIN_MODEL_NAME = settings.MAIN_MODEL_NAME

# 子模型配置 (MiniMax)
SUB_API_KEY = settings.SUB_API_KEY
SUB_BASE_URL = settings.SUB_BASE_URL
SUB_MODEL_NAME = settings.SUB_MODEL_NAME

# 创建模型客户端
# 主模型客户端(协调Agent使用)
main_model_client = AsyncOpenAI(
    base_url=MAIN_BASE_URL,
    api_key=MAIN_API_KEY
)
# 子模型客户端(干活的子Agent使用)
sub_model_client = AsyncOpenAI(
    base_url=SUB_BASE_URL,
    api_key=SUB_API_KEY
)

# 创建主调度模型
main_model = OpenAIChatCompletionsModel(
    model=MAIN_MODEL_NAME,
    openai_client=main_model_client)

# 创建子调度模型
sub_model = OpenAIChatCompletionsModel(
    model=SUB_MODEL_NAME,
    openai_client=sub_model_client)
