# 导入依赖项
from dotenv import load_dotenv
import os
from nylas import Client
from flask import Flask, request, redirect, url_for, session, jsonify
from flask_session.__init__ import Session
from nylas.models.auth import URLForAuthenticationConfig
from nylas.models.auth import CodeExchangeRequest
from datetime import datetime, timedelta
import requests
from urllib.parse import unquote
# 加载环境变量
load_dotenv()

# 创建应用
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# 初始化 Nylas 客户端
nylas = Client(
    api_key=os.environ.get("NYLAS_API_KEY"),
    api_uri=os.environ.get("NYLAS_API_URI"),
)

query_params_decoded = None
# Main route for OAuth exchange and event creation
@app.route("/oauth/exchange", methods=["GET","POST"])
def oauth_exchange():
    if "grant_id" not in session:
        if "code" not in request.args:
            # If code not present in request, redirect to login page
            config = URLForAuthenticationConfig({
                "client_id": os.environ.get("NYLAS_CLIENT_ID"), 
                "redirect_uri" : "http://localhost:8080/oauth/exchange"
            })
            url = nylas.auth.url_for_oauth2(config)
            session["query_params"] = request.query_string
            print(session)

            # 解码 query_params
            global query_params_decoded 
            query_params_decoded = unquote(session["query_params"].decode("utf-8"))
            print(query_params_decoded)
            # query_params_decoded = query_params_decoded.replace(' ', r'%20')
            # 获取 original_url
            # original_url = "http://localhost:8080/oauth/exchange"

            # 组成完整的 URL
            # complete_url = "http://localhost:8080/oauth/exchange?" + query_params_decoded
            return redirect(url)
        else:
            # If code present, exchange it for token and set grant_id in session
            code = request.args.get("code")
            exchangeRequest = CodeExchangeRequest({
                "redirect_uri": "http://localhost:8080/oauth/exchange",
                "code": code,
                "client_id": os.environ.get("NYLAS_CLIENT_ID")
            })
            exchange = nylas.auth.exchange_code_for_token(exchangeRequest)
            session["grant_id"] = exchange.grant_id
            
            # Create event
            return create_event()
    else:
        # If grant_id exists, directly create event
        return create_event()


def create_event():
    redirect_uri="http://localhost:8080/oauth/exchange"
    if "grant_id" not in session:
        return redirect(redirect_uri)
    
    # 从查询参数中获取start_time、end_time和title
    start_time_str = request.args.get("start_time")
    end_time_str = request.args.get("end_time")
    title = request.args.get("title", "Your event title here")

    if start_time_str is None and end_time_str is None:
        time_str = query_params_decoded.split('&')
        start_time_str = time_str[0].split('=')[1]
        print(start_time_str)
        end_time_str = time_str[1].split('=')[1]
        print(end_time_str)
        title = time_str[2].split('=')[1]
        print(title)
        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
    elif start_time_str is None:
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        start_time = end_time - timedelta(minutes=10)
    elif end_time_str is None:
        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_time = start_time + timedelta(minutes=10)
    else:
        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")


    # if start_time_str is None and end_time_str is not None:
    #     now = datetime.now()
    #     start_time = datetime.now()
    # else:
    #     start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    
    # if end_time_str is None:
    #     end_time = start_time + timedelta(minutes=10)
    # else:
    #     end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")


    start_time_unix = int(start_time.timestamp())
    end_time_unix = int(end_time.timestamp())
    query_params = {"calendar_id": session["calendar"]}

    request_body = {
        "when": {
            "start_time": start_time_unix,
            "end_time": end_time_unix,
        },
        "title": title
    }
    print(request_body)
    try:
        event = nylas.events.create(session["grant_id"], query_params=query_params, request_body=request_body)
        return "Event created successfully"
    except Exception as e:
        return f'Error creating event: {e}'


# @app.route('/external_calendar',methods=['GET','POST'])
# def external_calendar():
#     # 构建请求体数据
#     request_body = {
#         "when": { 
#             "start_time": "2024-03-05 19:00:00",
#             "end_time": "2024-03-05 22:00:00",    
#         },
#         "title": "test event"
#     }
#     # 提取查询参数
#     when_params = request_body.get("when")
#     title = request_body.get("title")

#     start_time = "start_time=" + when_params.get("start_time")
#     end_time = "end_time=" + when_params.get("end_time")
#     title = "title=" + title

#     # 将查询参数添加到 URL 中
#     api_url = "http://localhost:8080/oauth/exchange?" + start_time + '&' + end_time + '&' + title
#     api_url = api_url.replace(' ', r'%20')
#     # 将请求体数据转换为查询字符串
#     print('api_url: ', api_url)
#     # 发起 POST 请求
#     response = requests.post(api_url)
    
#     # 检查响应状态码
#     if response.status_code == 200:
#         return redirect(api_url)
#     else:
#         print("Error:", response.status_code)
    
#     # # 返回响应数据给用户
#     # return response.text

# @app.route('/clear-session', methods=['GET'])
# def clear_session():
#     # 移除特定的会话变量
#     session.pop('grant_id', None)  # 如果 'grant_id' 存在则移除，否则不执行任何操作
#     session.pop('query_params', None)
#     return "Session cleared successfully"


# 运行应用程序
if __name__ == "__main__":
    app.run()
