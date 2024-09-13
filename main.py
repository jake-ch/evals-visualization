import json
import logging
import os
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd
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
    st.session_state.filenames = []
    st.session_state.measures = defaultdict(lambda: defaultdict(list))


def load_eval_artifact(uploaded_file: UploadedFile):
    ext_path = TEMP_DIR / uploaded_file.name
    with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
        zip_ref.extractall(ext_path)

    jsonl_files = [
        os.path.join(ext_path, f) for f in os.listdir(ext_path) if f.endswith(".jsonl")
    ]

    result = {}
    for filename in jsonl_files:
        final_report, eval_name = None, None
        with open(filename) as f:
            for line in f:
                data = json.loads(line)
                if "final_report" in data:
                    final_report = data["final_report"]
                if "spec" in data:
                    eval_name = data["spec"]["run_config"]["eval_spec"]["args"][
                        "testset_path"
                    ]
        result[eval_name] = final_report

    result = dict(sorted(result.items()))
    return result


def main():
    file = st.file_uploader("Upload artifact file", type=["zip"])
    if file is not None:
        reports = load_eval_artifact(file)
        filename = file.name.split(".")[0] if "." in file.name else file.name
        st.session_state.filenames.append(filename)

        measures = st.session_state.measures

        for eval_name, report in reports.items():
            if eval_name.startswith("alf_fcagent") or eval_name.startswith(
                "alf_kbagent"
            ):
                # accuracy: overall
                measures[eval_name]["overall"].append(report["overall"]["accuracy"])
                # accuracy: per testfile
                for testfile, result in report["per_testfile"].items():
                    measures[eval_name][testfile].append(result["accuracy"])
            elif eval_name.startswith("alf_faq"):
                measures[eval_name + "/overall"]["retrieval_correct"].append(
                    report["metric"]["overall"]["retrieval_correct"]
                )
                measures[eval_name + "/overall"]["referenced_correct"].append(
                    report["metric"]["overall"]["referenced_correct"]
                )
            elif eval_name.startswith("alf_rag"):
                # fact check metrics
                measures[eval_name + "/fact_check"]["accuracy"].append(
                    report["fact_check"]["metrics"]["accuracy"]
                )
                measures[eval_name + "/fact_check"]["precision"].append(
                    report["fact_check"]["metrics"]["precision"]
                )
                measures[eval_name + "/fact_check"]["recall"].append(
                    report["fact_check"]["metrics"]["recall"]
                )
                # ragas
                measures[eval_name + "/ragas"]["faithfulness"].append(
                    report["ragas"]["faithfulness"]
                )
                measures[eval_name + "/ragas"]["answer_correctness"].append(
                    report["ragas"]["answer_correctness"]
                )
                measures[eval_name + "/ragas"]["answer_relevancy"].append(
                    report["ragas"]["answer_relevancy"]
                )

        for eval_name, measure_per_eval in measures.items():
            with st.expander(eval_name, expanded=False):
                df = pd.DataFrame(
                    [ms for ms in measure_per_eval.values()],
                    index=list(measure_per_eval.keys()),
                    columns=[filename for filename in st.session_state.filenames],
                )
                st.bar_chart(df, stack=False, horizontal=True)


if __name__ == "__main__":
    main()
