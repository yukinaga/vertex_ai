# 必要なライブラリをインストール（またはアップグレード）
# ノートブックのセルで初めて実行する際は、! を先頭につけます
!pip install --upgrade google-cloud-aiplatform kfp --quiet

import kfp
from kfp import dsl
from kfp.dsl import component, Input, Output, Artifact
from google.cloud import aiplatform

# --- 1. 自分の環境に合わせて、以下の3つの変数を編集してください ---

# 1. あなたのGoogle Cloud プロジェクトID
PROJECT_ID = "YOUR_PROJECT_ID"  # 例: "my-gcp-project-123"

# 2. パイプラインの実行に使いたいリージョン
REGION = "YOUR_REGION"  # 例: "us-central1"

# 3. 事前に作成したGCSバケットのURI
#    （末尾に / は不要です）
BUCKET_URI = "gs://YOUR_BUCKET_NAME"  # 例: "gs://my-pipeline-bucket-unique-name"

# -------------------------------------------------------------


# --- 2. パイプラインの「部品（コンポーネント）」を定義 ---

@component(
    base_image="python:3.9",  # この部品が動く環境
    packages_to_install=["google-cloud-storage"], # 必要なライブラリ
)
def say_hello() -> str:
    """
    単純に "Hello!" という文字列を返すコンポーネント
    """
    message = "Hello!"
    print(f"コンポーネント 1: メッセージ '{message}' を返します。")
    return message


@component(
    base_image="python:3.9",
    packages_to_install=["google-cloud-storage"],
)
def print_message(message: str):
    """
    前のコンポーネントからメッセージを受け取り、
    " Vertex AI!" を付けてログに出力するコンポーネント
    """
    full_message = f"{message} Vertex AI Pipelines!"
    print(f"コンポーネント 2: 最終的なメッセージ '{full_message}'")
    

# --- 3. パイプライン（組立ライン）の設計図を定義 ---

@dsl.pipeline(
    name="my-first-demo-pipeline",
    description="2つのコンポーネントをつなげる簡単なデモ"
)
def simple_pipeline_demo(
    # パイプライン実行時に外から渡すこともできる
    start_message: str = "Hello!" 
):
    # 1番目の部品（タスク）を実行
    # start_message はこのパイプライン関数に渡されたものを使う
    task_1 = say_hello()
    
    # 2番目の部品（タスク）を実行
    # task_1 の "output" (戻り値) を、task_2 の "message" (入力) につなげる
    task_2 = print_message(message=task_1.output)


# --- 4. パイプラインをコンパイル（JSONファイルに変換） ---

# パイプラインをJSONファイルにコンパイル（変換）します。
# これがVertex AIに「実行して」と渡す設計図の実体です。
PIPELINE_JSON = "simple_pipeline_demo.json"

kfp.compiler.Compiler().compile(
    pipeline_func=simple_pipeline_demo,
    package_path=PIPELINE_JSON
)

print(f"パイプラインが {PIPELINE_JSON} にコンパイルされました。")


# --- 5. パイプラインを実行 ---

print("Vertex AI SDK を初期化します...")
aiplatform.init(
    project=PROJECT_ID,
    location=REGION,
    staging_bucket=BUCKET_URI
)

print("パイプラインジョブを作成します...")
job = aiplatform.PipelineJob(
    display_name="demo-pipeline-run",  # Google Cloudコンソールに表示される名前
    template_path=PIPELINE_JSON,       # コンパイルしたJSONファイルのパス
    pipeline_root=f"{BUCKET_URI}/pipeline-root", # パイプラインの成果物を置く場所
)

print("パイプラインを実行します...")
job.run()

print("\nパイプラインが実行開始されました！")
print("以下のリンクからGoogle Cloudコンソールで実行状況を確認できます:")
print(f"https://console.cloud.google.com/vertex-ai/locations/{REGION}/pipelines/runs/{job.name}?project={PROJECT_ID}")
