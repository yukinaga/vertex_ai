# 必要なライブラリをインストール（またはアップグレード）
# scikit-learn も追加（コンポーネント内で使うため）
!pip install --upgrade google-cloud-aiplatform kfp scikit-learn pandas --quiet

import kfp
from kfp import dsl
from kfp.dsl import (
    component,
    Input,
    Output,
    Dataset,  # データセット成果物
    Model,    # モデル成果物
    Metrics   # メトリクス成果物
)
from google.cloud import aiplatform

# ==============================================================================
# 1. 基本設定 (実行前にここを編集してください)
# ==============================================================================

# あなたのGoogle Cloud プロジェクトID
PROJECT_ID = "YOUR_PROJECT_ID"  # 例: "my-gcp-project-123"

# パイプラインの実行に使いたいリージョン
REGION = "YOUR_REGION"  # 例: "us-central1"

# パイプラインの成果物を保存するためのGCSバケット
BUCKET_URI = "gs://YOUR_BUCKET_NAME"  # 例: "gs://my-pipeline-bucket-unique-name"

# このパイプラインのユニークな名前
PIPELINE_NAME = "ml-pipeline-practical-demo"

# ==============================================================================
# 2. コンポーネントの定義 (MLパイプラインの「部品」)
# ==============================================================================

# --- コンポーネント 1: データ準備 ---
@component(
    base_image="python:3.10", # 軽量な公式Pythonイメージを使用
    packages_to_install=["pandas", "scikit-learn"], # 必要なライブラリだけ指定
)
def prepare_data(
    output_dataset: Output[Dataset] # 出力として「データセット成果物」を指定
):
    """
    scikit-learnのIrisデータセットをロードし、
    CSVファイルとしてGCSに出力します。
    """
    import pandas as pd
    from sklearn.datasets import load_iris

    print("Irisデータセットをロードしています...")
    iris = load_iris()
    data = pd.DataFrame(data=iris.data, columns=iris.feature_names)
    data['target'] = iris.target

    # output_dataset.path は、Vertex AIが自動的に用意するGCS上の一時ファイルパスです
    csv_path = output_dataset.path + ".csv" # kfp v2はディレクトリパスを渡すため .csv を追記
    print(f"データをCSVとして {csv_path} に保存します...")
    data.to_csv(csv_path, index=False)
    
    # メタデータを保存（オプションだが推奨）
    output_dataset.metadata["data_shape"] = data.shape
    output_dataset.metadata["target_names"] = iris.target_names.tolist()


# --- コンポーネント 2: モデル訓練 ---
@component(
    base_image="python:3.10",
    packages_to_install=["pandas", "scikit-learn", "joblib"],
)
def train_model(
    input_dataset: Input[Dataset], # 入力として「データセット成果物」を受け取る
    output_model: Output[Model]    # 出力として「モデル成果物」を指定
):
    """
    受け取ったCSVデータを使って、簡単なロジスティック回帰モデルを訓練し、
    モデルファイルをGCSに出力します。
    """
    import pandas as pd
    import joblib
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split

    # input_dataset.path は、前のステップが保存したGCS上のファイルパスです
    csv_path = input_dataset.path + ".csv"
    print(f"{csv_path} からデータを読み込みます...")
    data = pd.read_csv(csv_path)

    X = data.drop('target', axis=1)
    y = data['target']
    
    # 簡単な訓練/テスト分割
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("ロジスティック回帰モデルを訓練します...")
    model = LogisticRegression(max_iter=200)
    model.fit(X_train, y_train)

    # テストデータでのスコアを計算（評価コンポーネントでもよい）
    score = model.score(X_test, y_test)
    print(f"モデルのテスト精度: {score}")

    # output_model.path は、Vertex AIが用意するGCS上の一時保存パスです
    # joblibを使ってモデルをシリアライズ（保存）します
    model_path = output_model.path + ".joblib"
    print(f"モデルを {model_path} に保存します...")
    joblib.dump(model, model_path)

    # メタデータを保存
    output_model.metadata["test_accuracy"] = score
    output_model.metadata["framework"] = "scikit-learn"


# --- コンポーネント 3: モデル評価 (簡略版) ---
@component(
    base_image="python:3.10",
    packages_to_install=["scikit-learn"], # このコンポーネントはjoblib不要
)
def evaluate_model(
    model_artifact: Input[Model], # 入力として「モデル成果物」を受け取る
    metrics: Output[Metrics]      # 出力として「メトリクス成果物」を指定
) -> str: # Pythonの基本型（str）も戻り値として返せる
    """
    受け取ったモデルのメタデータ（訓練時に保存した精度）を読み取り、
    Metrics成果物として保存します。
    """
    print("モデルのメタデータを読み取っています...")
    
    # 訓練ステップで保存したメタデータを取得
    test_accuracy = model_artifact.metadata["test_accuracy"]
    
    print(f"メタデータから取得した精度: {test_accuracy}")

    # Vertex AI UIの「指標」タブに表示するための処理
    metrics.log_metric("accuracy", test_accuracy)
    
    # 評価結果のサマリーを文字列として返す
    summary = f"Evaluation completed. Accuracy: {test_accuracy:.4f}"
    return summary


# ==============================================================================
# 3. パイプラインの定義 (「組立ライン」の設計図)
# ==============================================================================

@dsl.pipeline(
    name=PIPELINE_NAME,
    description="データ準備・訓練・評価を行う実践的なデモ"
)
def practical_ml_pipeline():
    """
    パイプラインの実行順序を定義します。
    """
    
    # 1. データ準備タスク
    prepare_data_task = prepare_data()
    
    # 2. 訓練タスク
    #    prepare_data_task の出力(output_dataset)を
    #    train_model_task の入力(input_dataset)に接続
    train_model_task = train_model(
        input_dataset=prepare_data_task.outputs["output_dataset"]
    )
    
    # 3. 評価タスク
    #    train_model_task の出力(output_model)を
    #    evaluate_model_task の入力(model_artifact)に接続
    evaluate_model_task = evaluate_model(
        model_artifact=train_model_task.outputs["output_model"]
    )
    
    # (オプション) 評価タスクの最終的な文字列出力をログに出す
    # このような「printするだけ」のコンポーネントを追加することも可能
    # print_summary_task = print_message(message=evaluate_model_task.output)


# ==============================================================================
# 4. パイプラインのコンパイル (JSONファイルへの変換)
# ==============================================================================

PIPELINE_JSON_PATH = f"{PIPELINE_NAME}.json"

print("パイプラインをコンパイルしています...")
kfp.compiler.Compiler().compile(
    pipeline_func=practical_ml_pipeline,
    package_path=PIPELINE_JSON_PATH
)

print(f"パイプラインが {PIPELINE_JSON_PATH} にコンパイルされました。")


# ==============================================================================
# 5. パイプラインの実行
# ==============================================================================

# パイプライン専用のGCSルートフォルダ
PIPELINE_ROOT_PATH = f"{BUCKET_URI}/{PIPELINE_NAME}-artifacts"

print(f"\nパイプラインの成果物保存場所: {PIPELINE_ROOT_PATH}")

# Vertex AI SDK を初期化
print("Vertex AI SDK を初期化します...")
aiplatform.init(
    project=PROJECT_ID,
    location=REGION,
    staging_bucket=BUCKET_URI 
)

# パイプライン実行ジョブを作成
print("パイプラインジョブを作成します...")
job = aiplatform.PipelineJob(
    display_name=f"{PIPELINE_NAME}-run",
    template_path=PIPELINE_JSON_PATH,
    pipeline_root=PIPELINE_ROOT_PATH,
    enable_caching=True # (費用節約) Trueにすると、入力が変わらないステップは再実行せずキャッシュを使う
)

# パイプラインを実行
print("パイプラインを実行します...")
job.run()

print("\nパイプラインが実行開始されました！")
print(f"GCSバケット ({PIPELINE_ROOT_PATH}) に成果物が保存されます。")
print("以下のリンクからGoogle Cloudコンソールで実行状況を確認できます:")
print(f"https://console.cloud.google.com/vertex-ai/locations/{REGION}/pipelines/runs/{job.name}?project={PROJECT_ID}")
