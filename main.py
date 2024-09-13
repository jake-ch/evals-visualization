import json
import logging
import os
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

TEMP_DIR = Path(__file__).parent / "./tmp/extracted"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

st.set_page_config(layout="wide")

# on first run, initialize session state
if "has_launched" not in st.session_state:
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    st.session_state.has_launched = True
    st.session_state.uploaded_files = []
    st.session_state.eval_logs = None


def load_eval_artifact(uploaded_file: UploadedFile):
    ext_path = TEMP_DIR / uploaded_file.name
    with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
        zip_ref.extractall(ext_path)

    json_files = [
        os.path.join(ext_path, f) for f in os.listdir(ext_path) if f.endswith(".json")
    ]

    result = {}
    for filename in json_files:
        # filename is TextIOWrapper. read it as json
        with open(filename) as rf:
            data = json.load(rf)
            if "spec" not in data:
                continue
            eval_name = data["spec"]["run_config"]["eval_spec"]["args"]["testset_path"]
        result[eval_name] = data

    result = dict(sorted(result.items()))
    return result


def main():
    file = st.file_uploader("Upload artifact file", type=["zip"])
    if file is not None and file.name not in [
        f.name for f in st.session_state.uploaded_files
    ]:
        st.session_state.uploaded_files.append(file)

    measures = defaultdict(list)
    for uploaded_file in st.session_state.uploaded_files:
        result = load_eval_artifact(uploaded_file)
        artifact = (
            uploaded_file.name.split(".")[0]
            if "." in uploaded_file.name
            else uploaded_file.name
        )

        for eval_name, data in result.items():
            report = data["final_report"]
            if eval_name.startswith("alf_fcagent") or eval_name.startswith(
                "alf_kbagent"
            ):
                for testfile, measure in report["per_testfile"].items():
                    row = {
                        "artifact": artifact,
                        "eval_name": eval_name,
                        "testfile": testfile,
                        "accuracy": measure["accuracy"],
                        "correct": measure["correct"],
                        "wrong": measure["all"] - measure["correct"],
                        "all": measure["all"],
                        "eval_logs": data["eval_logs"][testfile],
                        "text": f"{measure['correct']}/{measure['all']}",
                    }
                    measures[eval_name].append(row)
            elif eval_name.startswith("alf_faq"):
                pass  # TODO
            elif eval_name.startswith("alf_rag"):
                pass  # TODO

    for eval_name, rows in measures.items():
        fig = go.Figure()
        df = pd.DataFrame(rows)
        for uploaded_file in st.session_state.uploaded_files:
            artifact = (
                uploaded_file.name.split(".")[0]
                if "." in uploaded_file.name
                else uploaded_file.name
            )
            artifact_df = df[df["artifact"] == artifact]
            fig.add_trace(
                go.Bar(
                    x=artifact_df["accuracy"].clip(lower=1e-4),
                    y=artifact_df["testfile"],
                    name=artifact,
                    orientation="h",
                    text=artifact_df["text"],
                    customdata=artifact_df["eval_logs"],
                    hovertemplate="accuracy: %{x:.3f}",
                    marker=dict(
                        color=px.colors.qualitative.D3[
                            df["artifact"].unique().tolist().index(artifact)
                        ]
                    ),
                )
            )
        fig.update_layout(
            barmode="group",
            height=600,
            xaxis_title="Accuracy",
            yaxis_title="Test File",
            title=eval_name,
        )
        event_dict = st.plotly_chart(fig, on_select="rerun", selection_mode="points")
        if event_dict["selection"]["points"]:
            testfile = event_dict["selection"]["points"][0]["y"]
            eval_logs = event_dict["selection"]["points"][0]["customdata"]
            open_modal(eval_logs, testfile)


@st.dialog("Evalution logs", width="large")
def open_modal(item: dict, title: str):
    st.header(title)
    st.code(json.dumps(item, ensure_ascii=False, indent=2), language="json")


if __name__ == "__main__":
    main()
