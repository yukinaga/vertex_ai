# 必要なライブラリをインストール（またはアップグレード）
!pip install --upgrade google-cloud-aiplatform kfp --quiet

import kfp
from kfp import dsl
from kfp.dsl import component
from google.cloud import aiplatform

# ==============================================================================
# 1. 基本設定 (実行前にここを編集してください)
# ==============================================================================

# あなたのGoogle Cloud プロジェクトID
PROJECT_ID = "YOUR_PROJECT_ID"  # 例: "my-gcp-project-123"

# パイプラインの実行に使いたいリージョン
REGION = "YOUR_REGION"  # 例: "us-central1"

# パイプラインの成果物を保存するためのGCSバケット
# このバケット直下に、パイプライン名のフォルダが自動作成されます。
BUCKET_URI = "gs://YOUR_BUCKET_NAME"  # 例: "gs://my-pipeline-bucket-unique-name"

# このパイプラインのユニークな名前
# コンパイルされるJSONファイル名や、GCSのフォルダ名として使われます。
PIPELINE_NAME = "my-first-demo-pipeline"

# ==============================================================================
# 2. コンポーネントの定義 (パイプラインの「部品」)
# ==============================================================================

@component(
    base_image="python:3.9", # この部品が動くコンテナイメージ
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
)
def print_message(message: str):
    """
    前のコンポーネントからメッセージを受け取り、
    " Vertex AI Pipelines!" を付けてログに出力するコンポーネント
    """
    # 前のステップから渡された 'message' を使って新しい文字列を作成
    full_message = f"{message} Vertex AI Pipelines!"
    print(f"コンポーネント 2: 最終的なメッセージ '{full_message}'")
    

# ==============================================================================
# 3. パイプラインの定義 (「組立ライン」の設計図)
# ==============================================================================

@dsl.pipeline(
    name=PIPELINE_NAME,
    description="2つのコンポーネントをつなげる簡単なデモ"
)
def simple_pipeline_demo(
    # パイプライン実行時に外から渡すこともできる
    start_message: str = "Hello!" 
):
    """
    パイプラインの実行順序を定義します。
    """
    # 1番目の部品（タスク）を実行
    task_1 = say_hello()
    
    # 2番目の部品（タスク）を実行
    # task_1 の "output" (戻り値) を、task_2 の "message" (入力) につなげる
    task_2 = print_message(message=task_1.output)


# ==============================================================================
# 4. パイプラインのコンパイル (JSONファイルへの変換)
# ==============================================================================

# パイプライン定義(Pythonコード)を、Vertex AIが実行可能な
# JSON形式のファイルにコンパイル（変換）します。
PIPELINE_JSON_PATH = f"{PIPELINE_NAME}.json" 

kfp.compiler.Compiler().compile(
    pipeline_func=simple_pipeline_demo,
    package_path=PIPELINE_JSON_PATH
)

print(f"パイプラインが {PIPELINE_JSON_PATH} にコンパイルされました。")


# ==============================================================================
# 5. パイプラインの実行
# ==============================================================================

# このパイプライン専用のGCS上の「ルートフォルダ」のパスを定義します。
# これにより、バケット内で他のパイプラインと成果物が混ざりません。
PIPELINE_ROOT_PATH = f"{BUCKET_URI}/{PIPELINE_NAME}-artifacts"

print(f"\nパイプラインの成果物保存場所: {PIPELINE_ROOT_PATH}")

# Vertex AI SDK を初期化
print("Vertex AI SDK を初期化します...")
aiplatform.init(
    project=PROJECT_ID,
    location=REGION,
    staging_bucket=BUCKET_URI # コンパイルしたJSON等を一時的に置く場所
)

# パイプライン実行ジョブを作成
print("パイプラインジョブを作成します...")
job = aiplatform.PipelineJob(
    display_name=f"{PIPELINE_NAME}-run",  # Google Cloudコンソールに表示される名前
    template_path=PIPELINE_JSON_PATH,      # コンパイルしたJSONファイルのパス
    pipeline_root=PIPELINE_ROOT_PATH,      # 実行結果（成果物）を保存するGCS上の場所
)

# パイプラインを実行（ジョブを送信）
print("パイプラインを実行します...")
job.run()

print("\nパイプラインが実行開始されました！")
print(f"GCSバケット ({PIPELINE_ROOT_PATH}) に成果物が保存されます。")
print("以下のリンクからGoogle Cloudコンソールで実行状況を確認できます:")
print(f"https://console.cloud.google.com/vertex-ai/locations/{REGION}/pipelines/runs/{job.name}?project={PROJECT_ID}")
