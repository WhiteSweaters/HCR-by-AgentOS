import sys
import os

# 获取当前文件的目录和项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(current_dir + "/.env")
api_key = os.environ.get("TOGETHER_API_KEY")

# 导入所需模块
from agentos.agent.agent import Agent
from agentos.memory import TemporaryMemory, Message, Role
from src.tools import *
from src.hcr_prompt import HCR_PROMPT, OUTPUT_PROMPT
from agentos.utils import call_model
import sqlite3


# 定义推荐系统类
class Recommendation:
    def __init__(self, api_key: str | None = None):
        # 初始化代理，配置模型和工具
        self.mediagent = Agent(
            name="mediagent",
            model={},
            tools=[
                search_by_id(),          # 按ID搜索历史体检记录
                search_by_other(),       # 按其他条件搜索工具
                recommend_by_age(),      # 按年龄推荐工具
                recommend_by_gender()    # 按性别推荐工具
            ],
            api_key=api_key
        )
        self.conn = sqlite3.connect('history.db')
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id TEXT,
                gender TEXT,
                age INTEGER,
                height INTEGER,
                weight INTEGER,
                medical_history TEXT,
                symptoms TEXT,
                recommendation TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def run(self, user_info):
        # 使用用户信息格式化提示词并运行代理
        self.mediagent.run(HCR_PROMPT.format(user_info))
        # 添加系统提示到记忆
        self.mediagent.memory.add_memory(Message(Role.SYSTEM, OUTPUT_PROMPT))
        # 调用模型生成响应
        response = call_model(self.mediagent.memory.memory, self.mediagent.api_key)
        # 将模型响应添加到记忆
        self.mediagent.memory.add_memory(Message(Role.ASSISTANT, response))
        # 打印记忆内容
        print("\n\n\n\n\n")
        print("==============================MEMORY==============================")
        for i in self.mediagent.memory.memory:
            print(f"【{i['role']}】")
            print(i['content'])
            print("------------")
        # 打印模型响应
        print("\n\n\n\n\n")
        print("=============================RESPONSE=============================")
        print(response)
        # 保存用户信息和推荐结果到数据库
        self.save_history(user_info, response)
        return response

    def save_history(self, user_info, recommendation):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO history (id, gender, age, height, weight, medical_history, symptoms, recommendation)
            VALUES (?,?,?,?,?,?,?,?)
        ''', (
            user_info['id'],
            user_info['gender'],
            user_info['age'],
            user_info['height'],
            user_info['weight'],
            user_info['medical_history'],
            user_info['symptoms'],
            recommendation
        ))
        self.conn.commit()

    def get_history(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM history WHERE id =?', (user_id,))
        return cursor.fetchall()



# re = Recommendation(api_key=api_key)
# info={"id":"426815","gender":"男","age":50,"height":"172cm","weight":"80kg","medical_history":"高血压","symptom":"头晕"}
# re.run(info)

