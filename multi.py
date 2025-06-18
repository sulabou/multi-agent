import streamlit as st
import time
from datetime import datetime, timedelta
import uuid
import boto3
import json
import pandas as pd
import plotly.express as px
from botocore.exceptions import ClientError
import re
import sys
import subprocess

# ページ設定
st.set_page_config(
    layout="wide", 
    page_title="AWS監視システム", 
    initial_sidebar_state="expanded"
)

# Bedrock エージェント設定
BEDROCK_AGENT_ID = "8VZ0IXID7B"
BEDROCK_AGENT_ALIAS_ID = "ODSLAX1DR8"

# エージェント設定
AGENTS = {
    "インフラ専門家": {
        "icon": "🏗️",
        "color": "#667eea",
        "description": "システム基盤・技術的問題の専門分析"
    },
    "運用管理専門家": {
        "icon": "⚙️", 
        "color": "#f093fb",
        "description": "運用手順・対応策の専門提案"
    },
    "セキュリティ専門家": {
        "icon": "🔒", 
        "color": "#4fd1c5",
        "description": "セキュリティリスクの評価と対策提案"
    }
}

# 美しい日本語UI用CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Noto Sans JP', sans-serif;
    }
    
    .alert-card {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        color: white;
        padding: 30px;
        border-radius: 20px;
        margin: 20px 0;
        box-shadow: 0 15px 35px rgba(255, 107, 107, 0.3);
    }
    
    .agent-status-thinking {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        animation: pulse 2s infinite;
        color: #8b4513;
        font-weight: 500;
    }
    
    .agent-status-complete {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        color: #2d5a27;
        font-weight: 500;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    .agent-response-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 25px;
        margin: 20px 0;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        border-left: 5px solid var(--agent-color);
    }
    
    .summary-section {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border-left: 4px solid #ff9800;
    }
    
    .analysis-column {
        background-color: var(--bg-color);
        padding: 20px;
        border-radius: 12px;
        height: 100%;
        min-height: 300px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .analysis-column h4 {
        margin-top: 0;
        color: var(--text-color);
        font-weight: 600;
        font-size: 1.1em;
        margin-bottom: 15px;
    }
    
    .analysis-column ul, .analysis-column ol {
        margin: 10px 0;
        padding-left: 20px;
    }
    
    .analysis-column li {
        margin: 8px 0;
        line-height: 1.6;
    }
    
    .analysis-column p {
        line-height: 1.7;
        margin: 10px 0;
    }
    
    .cause-column {
        --bg-color: #e3f2fd;
        --text-color: #1565c0;
    }
    
    .action-column {
        --bg-color: #fff8e1;
        --text-color: #ef6c00;
    }
    
    .prevention-column {
        --bg-color: #e8f5e9;
        --text-color: #2e7d32;
    }
    
    .urgency-badge {
        background-color: #ff9800;
        color: white;
        padding: 12px 24px;
        border-radius: 30px;
        display: inline-block;
        margin-bottom: 25px;
        font-weight: bold;
        font-size: 1.1em;
    }
    
    .urgency-high {
        background-color: #f44336;
    }
    
    .urgency-medium {
        background-color: #ff9800;
    }
    
    .urgency-low {
        background-color: #4caf50;
    }
    
    .no-alarms-message {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        border-radius: 15px;
        padding: 30px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
    }
    
    .agent-message {
        padding: 12px 18px;
        border-radius: 12px;
        margin: 8px 0;
        max-width: 85%;
        line-height: 1.5;
    }
    
    .agent-message.agent1 {
        background-color: #e3f2fd;
        margin-right: auto;
        border-top-left-radius: 4px;
    }
    
    .agent-message.agent2 {
        background-color: #f1f8e9;
        margin-left: auto;
        border-top-right-radius: 4px;
    }
    
    .agent-message.agent3 {
        background-color: #fff3e0;
        margin-right: auto;
        border-top-left-radius: 4px;
    }
    
    .agent-name {
        font-weight: 600;
        margin-bottom: 8px;
        font-size: 0.95em;
    }
    
    .conversation-compact {
        max-height: 600px;
        overflow-y: auto;
        padding: 15px;
        border: 1px solid #eee;
        border-radius: 8px;
        margin-bottom: 20px;
        background-color: #fafafa;
    }
    
    .conversation-content p {
        margin: 0.4em 0 !important;
        line-height: 1.5 !important;
    }
    
    .conversation-content ul,
    .conversation-content ol {
        margin: 0.5em 0 0.5em 1.2em !important;
        padding-left: 0.5em !important;
    }
    
    .conversation-content li {
        margin: 0.2em 0 !important;
        padding: 0 !important;
        line-height: 1.5 !important;
    }
    
    .conversation-content h1, 
    .conversation-content h2,
    .conversation-content h3,
    .conversation-content h4 {
        margin: 0.8em 0 0.4em 0 !important;
        line-height: 1.3 !important;
    }
    
    .aws-qa-section {
        background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf1 100%);
        border-radius: 20px;
        padding: 30px;
        margin: 30px 0;
        border: 2px solid #4a90e2;
        box-shadow: 0 10px 25px rgba(74, 144, 226, 0.15);
    }
    
    .aws-qa-title {
        color: #2c5aa0;
        font-size: 1.5em;
        font-weight: 600;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .aws-qa-input {
        width: 100%;
        padding: 15px 20px;
        border: 2px solid #4a90e2;
        border-radius: 15px;
        font-size: 1.1em;
        background: white;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    
    .aws-qa-input:focus {
        outline: none;
        border-color: #2c5aa0;
        box-shadow: 0 6px 15px rgba(74, 144, 226, 0.3);
    }
    
    .aws-qa-response {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin-top: 20px;
        border-left: 4px solid #4a90e2;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

def initialize_session():
    """セッション状態の初期化（シークレット対応版）"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if "agent_responses" not in st.session_state:
        st.session_state.agent_responses = {}
        
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
        
    if "show_details" not in st.session_state:
        st.session_state.show_details = {}
        
    # AWS-QA関連のセッション状態を初期化
    if "aws_qa_question" not in st.session_state:
        st.session_state.aws_qa_question = ""
        
    if "aws_qa_response" not in st.session_state:
        st.session_state.aws_qa_response = ""
        
    if "aws_qa_history" not in st.session_state:
        st.session_state.aws_qa_history = []
        
    # リージョン設定
    region = st.sidebar.selectbox(
        "AWSリージョン", 
        ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "ap-northeast-1"], 
        index=3
    )
    
    # AWS クライアント初期化（シークレット対応）
    if "clients" not in st.session_state:
        try:
            # Streamlit Cloudのシークレットをチェック
            if hasattr(st, 'secrets') and "AWS" in st.secrets:
                # シークレットから認証情報を取得
                aws_access_key_id = st.secrets["AWS"]["AWS_ACCESS_KEY_ID"]
                aws_secret_access_key = st.secrets["AWS"]["AWS_SECRET_ACCESS_KEY"]
                aws_region = st.secrets["AWS"].get("AWS_DEFAULT_REGION", region)
                
                st.session_state.clients = {
                    "cloudwatch": boto3.client(
                        "cloudwatch", 
                        region_name=aws_region,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key
                    ),
                    "bedrock_agent": boto3.client(
                        "bedrock-agent-runtime", 
                        region_name=aws_region,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key
                    )
                }
                st.sidebar.success("AWS接続成功（シークレット使用）")
            else:
                # ローカル環境では既存の方法を使用
                st.session_state.clients = {
                    "cloudwatch": boto3.client("cloudwatch", region_name=region),
                    "bedrock_agent": boto3.client("bedrock-agent-runtime", region_name=region)
                }
                st.sidebar.success("AWS接続成功（ローカル認証）")
                
        except Exception as e:
            st.sidebar.error(f"AWS接続エラー: {str(e)}")
            # デバッグ情報を追加
            if hasattr(st, 'secrets'):
                if "AWS" in st.secrets:
                    st.sidebar.info("シークレットは設定されています")
                    # キーの存在確認（値は表示しない）
                    keys_present = []
                    if "AWS_ACCESS_KEY_ID" in st.secrets["AWS"]:
                        keys_present.append("ACCESS_KEY_ID")
                    if "AWS_SECRET_ACCESS_KEY" in st.secrets["AWS"]:
                        keys_present.append("SECRET_ACCESS_KEY")
                    if "AWS_DEFAULT_REGION" in st.secrets["AWS"]:
                        keys_present.append("DEFAULT_REGION")
                    st.sidebar.info(f"設定済みキー: {', '.join(keys_present)}")
                else:
                    st.sidebar.warning("シークレットにAWSセクションが見つかりません")
            else:
                st.sidebar.warning("シークレットが利用できません")
            st.session_state.clients = None
            
    # その他の初期化
    if "alarms" not in st.session_state:
        st.session_state.alarms = []
        
    if "selected_alarm" not in st.session_state:
        st.session_state.selected_alarm = None
        
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()
        
    if "agent_conversations" not in st.session_state:
        st.session_state.agent_conversations = []
        
    if "analysis_summary" not in st.session_state:
        st.session_state.analysis_summary = {}

def get_active_alarms(client):
    """CloudWatchから有効なアラームを取得"""
    try:
        response = client.describe_alarms(
            StateValue='ALARM',
            MaxRecords=10
        )
        return response.get('MetricAlarms', [])
    except Exception as e:
        st.error(f"CloudWatchからアラーム情報の取得に失敗しました: {str(e)}")
        return []

def get_metric_data(client, namespace, metric_name, dimensions, start_time, end_time, period=60):
    """メトリックデータを取得"""
    try:
        response = client.get_metric_data(
            MetricDataQueries=[{
                'Id': 'metric1',
                'MetricStat': {
                    'Metric': {
                        'Namespace': namespace,
                        'MetricName': metric_name,
                        'Dimensions': dimensions
                    },
                    'Period': period,
                    'Stat': 'Average'
                }
            }],
            StartTime=start_time,
            EndTime=end_time
        )
        if 'MetricDataResults' in response and len(response['MetricDataResults']) > 0:
            result = response['MetricDataResults'][0]
            timestamps = result.get('Timestamps', [])
            values = result.get('Values', [])
            if timestamps and values:
                return pd.DataFrame({
                    'timestamp': timestamps,
                    'value': values
                })
        return None
    except Exception as e:
        st.error(f"メトリックデータの取得に失敗しました: {str(e)}")
        return None

def display_alarm_info(alarm):
    """アラーム情報の表示"""
    st.markdown(f"""
    <div class="alert-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="margin: 0; color: white;">🚨 緊急アラート</h2>
                <h3 style="margin: 10px 0; color: white;">{alarm['name']}</h3>
                <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.9);">
                    {alarm['reason']}
                </p>
                <div style="margin-top: 15px;">
                    <span style="background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 10px; font-size: 0.9em;">
                        緊急度: {alarm['severity']} | サービス: {alarm['service']}
                    </span>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 4em;">⚠️</div>
                <p style="margin: 5px 0 0 0; color: rgba(255,255,255,0.8); font-size: 0.9em;">
                    {alarm['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_metric_chart(cloudwatch, alarm):
    """アラームに関連するメトリックのグラフを表示"""
    if 'MetricName' in alarm and 'Namespace' in alarm:
        st.caption(f"{alarm['MetricName']}の推移")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=3)

        dimensions = []
        if 'Dimensions' in alarm and isinstance(alarm['Dimensions'], list):
            dimensions = alarm['Dimensions']

        metric_df = get_metric_data(
            cloudwatch,
            alarm['Namespace'],
            alarm['MetricName'],
            dimensions,
            start_time,
            end_time,
            period=60
        )

        if metric_df is not None and not metric_df.empty:
            try:
                metric_df['timestamp'] = pd.to_datetime(metric_df['timestamp'])
                fig = px.line(
                    metric_df, 
                    x='timestamp', 
                    y='value',
                    labels={'timestamp': '時間', 'value': f"{alarm['MetricName']}"}
                )
                if 'Threshold' in alarm:
                    fig.add_hline(
                        y=alarm['Threshold'], 
                        line_dash="dash", 
                        line_color="red",
                        annotation_text="閾値"
                    )
                fig.update_layout(
                    height=250,
                    margin=dict(l=0, r=0, t=10, b=0),
                    template="plotly_white",
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"グラフ描画中にエラーが発生しました: {str(e)}")
        else:
            st.info("メトリックデータが取得できませんでした")

def display_agent_conversations():
    """エージェント間の会話を表示"""
    if not st.session_state.agent_conversations:
        st.info("エージェント間の会話はまだありません")
        return
    st.markdown("### 🤖 エージェント間の会話")
    # 会話サマリーを常に表示
    agent_counts = {}
    for conv in st.session_state.agent_conversations:
        agent_name = conv.get("agent", "不明なエージェント")
        if agent_name != "メインエージェント":
            agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1
    st.markdown("#### 会話サマリー")
    for agent_name, count in agent_counts.items():
        if agent_name in AGENTS:
            icon = AGENTS[agent_name]["icon"]
        else:
            icon = "🤖"
        st.markdown(f"- {icon} **{agent_name}**: {count}件のメッセージ")
    # 詳細な会話を折りたたみ可能なexpanderで表示
    with st.expander("💬 エージェント会話の詳細", expanded=False):
        st.markdown('<div class="conversation-compact">', unsafe_allow_html=True)
        for i, conversation in enumerate(st.session_state.agent_conversations):
            agent_name = conversation.get("agent", "不明なエージェント")
            message = conversation.get("message", "")
            # 空のメッセージや短すぎるメッセージのみスキップ
            if not message or len(message.strip()) < 10:
                continue
            agent_class = f"agent{(i % 3) + 1}"
            if agent_name in AGENTS:
                agent = AGENTS[agent_name]
                icon = agent.get("icon", "🤖")
            else:
                icon = "🤖"
            message = message.replace(". ", "。")
            st.markdown(f"""
<div class="agent-message {agent_class}">
<div class="agent-name">{icon} {agent_name}</div>
<div class="conversation-content" style="white-space: pre-line;">{message}</div>
</div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def create_agent_prompt_from_alarm(alarm_data):
    """アラームデータからエージェントプロンプトを生成"""
    alarm_json = json.dumps(alarm_data, default=str, indent=2)
    return f"""以下のCloudWatchアラートを分析して、以下のポイントを詳細に解説してください:
1. 【緊急度】: このアラートの緊急度と重要度を評価してください（高/中/低）
2. 【原因分析】: 考えられる技術的な根本原因を詳細に説明してください
3. 【対応策】: この問題に対する短期的な緊急対応と、長期的な解決策を提案してください
4. 【予防策】: 同様の問題が再発しないための予防策を提案してください

CloudWatchアラート:
{alarm_json}

技術的な詳細を含めて回答してください。AWS運用チームへの報告書として使用できるような包括的な分析を提供してください。
回答は日本語でお願いします。"""

def create_aws_qa_prompt(question):
    """AWS-QA専用のプロンプトを生成"""
    return f"""AWS関連の質問に対して、専門的で詳細な回答を提供してください。

質問: {question}

以下の観点から回答してください：
1. 技術的な詳細と背景
2. ベストプラクティス
3. 注意点やリスク
4. 実装例や設定方法（該当する場合）
5. 関連するAWSサービスとの連携

回答は日本語で、AWS運用担当者が理解しやすい形で提供してください。"""

def invoke_bedrock_agent(client, session_id, prompt):
    """Bedrockエージェントを呼び出す"""
    try:
        return client.invoke_agent(
            agentId=BEDROCK_AGENT_ID,
            agentAliasId=BEDROCK_AGENT_ALIAS_ID,
            sessionId=session_id,
            enableTrace=True,
            inputText=prompt,
        )
    except Exception as e:
        st.error(f"Bedrockエージェント呼び出しエラー: {str(e)}")
        return None

def handle_trace_event(event):
    """トレースイベントの処理（改善版）"""
    if "trace" not in event or "trace" not in event["trace"] or "orchestrationTrace" not in event["trace"]["trace"]:
        return
    
    trace = event["trace"]["trace"]["orchestrationTrace"]
    
    agent_display_names = {
        "infra-expert": "インフラ専門家",
        "ops-expert": "運用管理専門家", 
        "security-expert": "セキュリティ専門家",
        "test-hirata-hikaku": "インフラ専門家",
        "test-hirata-v1": "運用管理専門家"
    }
    
    if "invocationInput" in trace:
        invocation_type = trace["invocationInput"].get("invocationType", "")
        if invocation_type == "AGENT_COLLABORATOR" and "agentCollaboratorInvocationInput" in trace["invocationInput"]:
            input_data = trace["invocationInput"]["agentCollaboratorInvocationInput"]
            original_agent_name = input_data.get("agentCollaboratorName", "不明なエージェント")
            display_name = agent_display_names.get(original_agent_name, original_agent_name)
            
            if "input" in input_data and "text" in input_data["input"]:
                # メインエージェントの指示を日本語で整理
                raw_message = input_data['input']['text']
                formatted_message = format_main_agent_message(raw_message)
                
                st.session_state.agent_conversations.append({
                    "agent": "メインエージェント",
                    "message": formatted_message
                })
    
    if "observation" in trace:
        obs_type = trace["observation"].get("type", "")
        if obs_type == "AGENT_COLLABORATOR" and "agentCollaboratorInvocationOutput" in trace["observation"]:
            output_data = trace["observation"]["agentCollaboratorInvocationOutput"]
            original_agent_name = output_data.get("agentCollaboratorName", "不明なエージェント")
            display_name = agent_display_names.get(original_agent_name, original_agent_name)
            
            if "output" in output_data and "text" in output_data["output"]:
                st.session_state.agent_conversations.append({
                    "agent": display_name,
                    "message": output_data['output']['text']
                })

def format_main_agent_message(raw_message):
    """メインエージェントのメッセージを日本語で整理"""
    try:
        # JSONデータが含まれている場合の処理
        if "AlarmName" in raw_message and "{" in raw_message:
            # アラーム情報を抽出
            alarm_name = ""
            state_reason = ""
            metric_name = ""
            threshold = ""
            
            # AlarmNameを抽出
            alarm_match = re.search(r'"AlarmName":\s*"([^"]+)"', raw_message)
            if alarm_match:
                alarm_name = alarm_match.group(1)
            
            # StateReasonを抽出
            reason_match = re.search(r'"StateReason":\s*"([^"]+)"', raw_message)
            if reason_match:
                state_reason = reason_match.group(1)
            
            # MetricNameを抽出
            metric_match = re.search(r'"MetricName":\s*"([^"]+)"', raw_message)
            if metric_match:
                metric_name = metric_match.group(1)
            
            # Thresholdを抽出
            threshold_match = re.search(r'"Threshold":\s*([0-9.]+)', raw_message)
            if threshold_match:
                threshold = threshold_match.group(1)
            
            # 日本語メッセージを構築
            formatted_message = f"""以下のCloudWatchアラートについて詳細な分析をお願いします：

📋 **アラート概要**
• アラート名: {alarm_name}
• メトリック: {metric_name}
• 閾値: {threshold}
• 状態: アラーム発生中

📊 **発生理由**
{state_reason}

🎯 **分析依頼内容**
このアラートの技術的な原因分析、適切な対応策、および今後の予防策について、AWS運用の観点から包括的な評価をお願いします。"""
            
            return formatted_message
        
        # 通常のメッセージの場合
        else:
            # 英語から日本語への基本的な置換
            message = raw_message
            message = message.replace("Please analyze", "以下について分析してください")
            message = message.replace("CloudWatch alarm", "CloudWatchアラート")
            message = message.replace("regarding", "に関して")
            message = message.replace("The alarm details are as follows", "アラートの詳細は以下の通りです")
            
            return message
            
    except Exception as e:
        # エラーが発生した場合はデフォルトメッセージ
        return "CloudWatchアラートの分析を開始します。各専門エージェントによる詳細な評価を実施中です。"

def handle_agent_response(response):
    """エージェントのレスポンスを処理"""
    if not response:
        return
        
    answer_parts = []
    
    with st.spinner("Bedrockエージェントからの応答を処理中..."):
        for event in response.get("completion", []):
            if "trace" in event:
                handle_trace_event(event)
            
            if "chunk" in event:
                chunk = event["chunk"]["bytes"].decode()
                answer_parts.append(chunk)
    
    return "".join(answer_parts)

def extract_analysis_summary(text):
    """分析結果から要約を抽出する（修正版）"""
    summary = {
        "緊急度": "中",
        "原因": "分析中...",
        "対応策": "分析中...",
        "予防策": "分析中..."
    }
    
    if not text:
        return summary
    
    # 緊急度を抽出
    urgency_patterns = [
        r"【緊急度】[:：]?\s*([高中低])",
        r"緊急度[:：]?\s*([高中低])",
        r"重要度[:：]?\s*([高中低])"
    ]
    
    for pattern in urgency_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            urgency = matches[0]
            summary["緊急度"] = urgency
            break
    
    # セクション別に内容を抽出
    sections = {
        "原因": ["【原因分析】", "原因分析", "Root Cause", "原因"],
        "対応策": ["【対応策】", "対応策", "Action Items", "対応"],
        "予防策": ["【予防策】", "予防策", "Prevention", "予防"]
    }
    
    for key, keywords in sections.items():
        for keyword in keywords:
            # セクションを抽出
            pattern = f"{re.escape(keyword)}.*?(?=【|$)"
            section_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            
            if section_match:
                section_text = section_match.group(0)
                # キーワードを除去
                section_text = re.sub(f"^{re.escape(keyword)}[:：]?", "", section_text).strip()
                
                # 箇条書きを抽出
                bullet_points = []
                
                # 様々な箇条書きパターンを検索
                patterns = [
                    r'[・\-\*•]\s*([^・\-\*•\n]+)',
                    r'\d+\.\s*([^\n]+)',
                    r'[①②③④⑤⑥⑦⑧⑨⑩]\s*([^\n]+)'
                ]
                
                for pattern in patterns:
                    points = re.findall(pattern, section_text)
                    if points:
                        for point in points:
                            cleaned_point = point.strip()
                            # 長すぎる場合は短縮
                            if len(cleaned_point) > 60:
                                cleaned_point = cleaned_point[:60] + "..."
                            if cleaned_point and len(cleaned_point) > 5:
                                bullet_points.append(cleaned_point)
                        break
                
                # 箇条書きが見つからない場合は文章から抽出
                if not bullet_points:
                    sentences = re.split(r'[。.]\s*', section_text)
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if sentence and len(sentence) > 10:
                            if len(sentence) > 50:
                                sentence = sentence[:50] + "..."
                            bullet_points.append(sentence)
                            if len(bullet_points) >= 3:
                                break
                
                # 結果を設定
                if bullet_points:
                    summary[key] = "\n".join([f"• {point}" for point in bullet_points[:3]])
                    break
    
    # デフォルト値の設定
    if summary["原因"] == "分析中...":
        summary["原因"] = "• CPU使用率の異常低下\n• アプリケーション処理の停止\n• システムリソースの問題"
    
    if summary["対応策"] == "分析中...":
        summary["対応策"] = "• インスタンス状態の確認\n• プロセス状況の調査\n• ログファイルの分析"
    
    if summary["予防策"] == "分析中...":
        summary["予防策"] = "• 監視設定の最適化\n• 定期的なヘルスチェック\n• アラート閾値の調整"
    
    return summary

def display_analysis_summary(summary):
    """分析結果の表示（修正版）"""
    st.markdown("## 📊 アラート分析結果")
    
    # 緊急度に応じたスタイル
    urgency = summary.get('緊急度', '中')
    urgency_class = "urgency-medium"
    if urgency == "高":
        urgency_class = "urgency-high"
    elif urgency == "低":
        urgency_class = "urgency-low"
    
    st.markdown(
        f"""
        <div class="urgency-badge {urgency_class}">
            ⚠️ 緊急度: {urgency}
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # 3カラムレイアウト
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔍 原因分析")
        cause_content = summary.get('原因', '分析中...')
        st.markdown(
            f"""
            <div class="analysis-column cause-column">
                <h4>考えられる技術的な根本原因</h4>
                <div style="white-space: pre-line; line-height: 1.6;">{cause_content}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown("### 🔧 対応策")
        action_content = summary.get('対応策', '分析中...')
        st.markdown(
            f"""
            <div class="analysis-column action-column">
                <h4>推奨される対応手順</h4>
                <div style="white-space: pre-line; line-height: 1.6;">{action_content}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown("### 🛡️ 予防策")
        prevention_content = summary.get('予防策', '分析中...')
        st.markdown(
            f"""
            <div class="analysis-column prevention-column">
                <h4>再発防止のための対策</h4>
                <div style="white-space: pre-line; line-height: 1.6;">{prevention_content}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

def convert_cloudwatch_alarm_to_display_format(alarm):
    """CloudWatchアラームを表示用フォーマットに変換"""
    service = "その他"
    if 'Namespace' in alarm:
        namespace = alarm['Namespace']
        if 'EC2' in namespace:
            service = "EC2"
        elif 'RDS' in namespace:
            service = "RDS"
        elif 'S3' in namespace:
            service = "S3"
        elif 'CloudFront' in namespace:
            service = "CloudFront"
        elif 'DynamoDB' in namespace:
            service = "DynamoDB"
    
    severity = "中"
    alarm_name = alarm.get('AlarmName', '不明なアラーム')
    if any(keyword in alarm_name.lower() for keyword in ['critical', 'high', '緊急']):
        severity = "高"
    elif any(keyword in alarm_name.lower() for keyword in ['warning', 'warn', '警告']):
        severity = "中"
    else:
        severity = "低"
    
    return {
        "name": alarm_name,
        "description": alarm.get('AlarmDescription', '説明なし'),
        "reason": alarm.get('StateReason', '理由不明'),
        "timestamp": alarm.get('StateUpdatedTimestamp', datetime.now()),
        "severity": severity,
        "service": service,
        "resource": alarm.get('Dimensions', [{}])[0].get('Value', '') if alarm.get('Dimensions') else ''
    }

def display_alarm_selection(alarms):
    """アラーム選択UI"""
    if not alarms:
        return None
        
    alarm_options = []
    for i, alarm in enumerate(alarms):
        alarm_name = alarm.get('AlarmName', f'アラーム {i+1}')
        service = "その他"
        if 'Namespace' in alarm:
            namespace = alarm['Namespace']
            if 'EC2' in namespace:
                service = "EC2"
            elif 'RDS' in namespace:
                service = "RDS"
            elif 'S3' in namespace:
                service = "S3"
            elif 'CloudFront' in namespace:
                service = "CloudFront"
            elif 'DynamoDB' in namespace:
                service = "DynamoDB"
        alarm_options.append(f"{alarm_name} ({service})")
    
    selected_index = st.selectbox(
        "分析するアラームを選択:",
        range(len(alarm_options)),
        format_func=lambda i: alarm_options[i]
    )
    
    return alarms[selected_index]

def display_no_alarms_message():
    """アラームがない場合のメッセージ表示"""
    st.markdown("""
    <div class="no-alarms-message">
        <h2 style="color: #2e7d32;">✅ アクティブなアラームはありません</h2>
        <p style="font-size: 1.2em; margin-top: 15px;">
            現在、AWS環境で検出されたアクティブなアラームはありません。<br>
            すべてのシステムが正常に動作しています。
        </p>
        <div style="margin-top: 20px; font-size: 4em;">🎉</div>
    </div>
    """, unsafe_allow_html=True)

def analyze_with_bedrock(alarm):
    """Bedrockを使用してアラームを分析"""
    if not st.session_state.clients or "bedrock_agent" not in st.session_state.clients:
        st.error("Bedrock接続が確立されていません")
        return False
    
    prompt = create_agent_prompt_from_alarm(alarm)
    st.session_state.agent_conversations = []
    
    with st.spinner("Bedrockエージェントによる分析を実行中..."):
        response = invoke_bedrock_agent(
            st.session_state.clients["bedrock_agent"],
            st.session_state.session_id,
            prompt
        )
        
        if response:
            final_response = handle_agent_response(response)
            
            if final_response:
                st.session_state.agent_responses["Bedrock分析結果"] = final_response
                st.session_state.analysis_summary = extract_analysis_summary(final_response)
                st.session_state.analysis_complete = True
                st.rerun()
                return True
    
    return False

def handle_aws_qa_question(question):
    """AWS-QA質問を処理"""
    if not st.session_state.clients or "bedrock_agent" not in st.session_state.clients:
        st.error("Bedrock接続が確立されていません")
        return False
    
    prompt = create_aws_qa_prompt(question)
    
    with st.spinner("AWS-QAエージェントが回答を生成中..."):
        response = invoke_bedrock_agent(
            st.session_state.clients["bedrock_agent"],
            st.session_state.session_id + "_aws_qa",  # 別のセッションIDを使用
            prompt
        )
        
        if response:
            answer_parts = []
            for event in response.get("completion", []):
                if "chunk" in event:
                    chunk = event["chunk"]["bytes"].decode()
                    answer_parts.append(chunk)
            
            final_response = "".join(answer_parts)
            
            if final_response:
                # 履歴に追加
                st.session_state.aws_qa_history.append({
                    "question": question,
                    "answer": final_response,
                    "timestamp": datetime.now()
                })
                
                st.session_state.aws_qa_response = final_response
                return True
    
    return False

def display_aws_qa_section():
    """AWS-QA専用セクションを表示"""
    st.markdown("""
    <div class="aws-qa-section">
        <div class="aws-qa-title">
            🤖 AWS-QA エージェント
            <span style="font-size: 0.8em; font-weight: normal; color: #666;">AWS関連の質問にお答えします</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 質問入力フォーム
    with st.form("aws_qa_form", clear_on_submit=True):
        question = st.text_area(
            "",
            placeholder="質問をどうぞ",
            height=100,
            key="aws_qa_input",
            help="AWS関連の技術的な質問、ベストプラクティス、トラブルシューティングなど、何でもお聞きください。"
        )
        
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            submit_button = st.form_submit_button("質問する", type="primary")
        with col2:
            clear_button = st.form_submit_button("履歴をクリア")
    
    # 質問処理
    if submit_button and question.strip():
        success = handle_aws_qa_question(question.strip())
        if success:
            st.rerun()
    
    # 履歴クリア処理
    if clear_button:
        st.session_state.aws_qa_history = []
        st.session_state.aws_qa_response = ""
        st.success("履歴をクリアしました")
        st.rerun()
    
    # 最新の回答を表示
    if st.session_state.aws_qa_response:
                    with st.expander("💡 AWS-QA エージェントの回答", expanded=False):
                        st.markdown(st.session_state.aws_qa_response)
    
    # 質問履歴を表示
    if st.session_state.aws_qa_history:
        with st.expander(f"📚 質問履歴 ({len(st.session_state.aws_qa_history)}件)", expanded=False):
            for i, item in enumerate(reversed(st.session_state.aws_qa_history[-5:])):  # 最新5件のみ表示
                st.markdown(f"""
                **質問 {len(st.session_state.aws_qa_history) - i}:** {item['question']}
                
                **回答:** {item['answer'][:200]}{'...' if len(item['answer']) > 200 else ''}
                
                *{item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}*
                
                ---
                """)

def main():
    """メイン関数"""
    initialize_session()
    
    st.title("🚨 AWS監視システム")
    st.markdown("### Amazon Bedrock マルチエージェントによる協調分析システム")
    
    # アラーム取得
    if st.session_state.clients and "cloudwatch" in st.session_state.clients:
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("🔄 更新", key="refresh_alarms"):
                st.session_state.last_refresh = datetime.now()
                with st.spinner("アラーム情報を更新中..."):
                    try:
                        st.session_state.alarms = get_active_alarms(st.session_state.clients["cloudwatch"])
                        st.success("アラーム情報を更新しました")
                    except Exception as e:
                        st.error(f"アラーム取得エラー: {str(e)}")
        
        with col1:
            st.caption(f"最終更新: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not st.session_state.alarms:
            try:
                with st.spinner("CloudWatchからアラーム情報を取得中..."):
                    st.session_state.alarms = get_active_alarms(st.session_state.clients["cloudwatch"])
            except Exception as e:
                st.error(f"アラーム取得エラー: {str(e)}")
    
    # アラーム処理
    if st.session_state.alarms:
        selected_alarm = display_alarm_selection(st.session_state.alarms)
        
        if selected_alarm:
            st.session_state.selected_alarm = selected_alarm
            
            alarm_display = convert_cloudwatch_alarm_to_display_format(selected_alarm)
            display_alarm_info(alarm_display)
            
            if st.session_state.clients and "cloudwatch" in st.session_state.clients:
                with st.expander("📊 メトリックデータ", expanded=False):
                    try:
                        display_metric_chart(st.session_state.clients["cloudwatch"], selected_alarm)
                    except Exception as e:
                        st.error(f"メトリック表示エラー: {str(e)}")
            
            st.markdown("---")
            
            if not st.session_state.analysis_complete:
                if st.button("🚀 Bedrockマルチエージェントによる分析を開始", key="start_analysis", type="primary"):
                    success = analyze_with_bedrock(selected_alarm)
                    if success:
                        st.success("✅ Bedrockによる分析が完了しました")
                        st.rerun()
            else:
                st.success("✅ 分析完了 - 以下の結果を確認してください")
                
                if st.session_state.analysis_summary:
                    display_analysis_summary(st.session_state.analysis_summary)
                
                display_agent_conversations()

                
                
                if "Bedrock分析結果" in st.session_state.agent_responses:
                    with st.expander("📝 詳細分析レポート", expanded=False):
                        st.markdown(st.session_state.agent_responses["Bedrock分析結果"])
    else:
        display_no_alarms_message()
    
    # AWS-QA専用セクションを下部に追加
    st.markdown("---")
    display_aws_qa_section()

    # サイドバー
    with st.sidebar:
        st.markdown("### 🎛️ システム情報")
        
        if st.session_state.clients and "cloudwatch" in st.session_state.clients:
            st.success("✅ AWS CloudWatch 接続済み")
        else:
            st.error("❌ AWS CloudWatch 未接続")
            st.info("AWS認証情報を設定してください")
            
        if st.session_state.clients and "bedrock_agent" in st.session_state.clients:
            st.success("✅ Amazon Bedrock 接続済み")
        else:
            st.error("❌ Amazon Bedrock 未接続")
            st.info("AWS認証情報を設定してください")
        
        st.markdown("### 📊 分析状況")
        if st.session_state.analysis_complete:
            st.success("✅ 分析完了")
        else:
            st.warning("⏳ 分析待機中")
        
        # AWS-QA状況を追加
        st.markdown("### 🤖 AWS-QA状況")
        if st.session_state.aws_qa_history:
            st.info(f"📚 質問履歴: {len(st.session_state.aws_qa_history)}件")
        else:
            st.info("💭 質問をお待ちしています")
        
        with st.expander("⚙️ Bedrock設定", expanded=False):
            agent_id = st.text_input("Bedrock Agent ID", value=st.session_state.get("bedrock_config", {}).get("agent_id", BEDROCK_AGENT_ID))
            agent_alias_id = st.text_input("Bedrock Agent Alias ID", value=st.session_state.get("bedrock_config", {}).get("agent_alias_id", BEDROCK_AGENT_ALIAS_ID))
           
            if st.button("設定を保存", key="save_bedrock_settings"):
                st.session_state.bedrock_config = {}
                st.session_state.bedrock_config["agent_id"] = agent_id
                st.session_state.bedrock_config["agent_alias_id"] = agent_alias_id
                st.success("Bedrock設定を保存しました")
                time.sleep(1)
                st.rerun()
        
        if st.button("🔄 システムリセット"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
