import streamlit as st
import json
from collections import defaultdict
from io import StringIO

st.set_page_config(layout="wide")

def load_record_jsonl(uploaded_file):
    spec, final_report, data = None, None, None
    file_data = StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    lines = file_data.strip().split("\n")
    data_groups = defaultdict(list)
    for i, line in enumerate(lines):
        obj = json.loads(line)
        if "spec" in obj:
            spec = obj["spec"]
        elif "final_report" in obj:
            final_report = obj["final_report"]
        else:
            data_groups[obj["sample_id"]].append(obj["data"])

    # merge each data group into a single dictionary
    data = []
    for sample_id, data_group in data_groups.items():
        merged_data = {}
        for data_dict in data_group:
            merged_data.update(data_dict)
        data.append(
            {
                "sample_id": sample_id,
                "data": merged_data,
            }
        )

    # sort data by sample_id, where sample_id format is: <eval_name>.<minor-version>.<id_to_sort>
    data.sort(key=lambda x: int(x["sample_id"].split(".")[-1]))

    return spec, final_report, data

def main():
    # set two columns layout, where first column is 1/3 of the page width
    col1, col2 = st.columns([1, 3])

    with col1:
        file = st.file_uploader("Upload record file", type="jsonl")
        if file is not None:
            spec, report, data = load_record_jsonl(file)
            # save spec, report, data to session state
            st.session_state.spec = spec
            st.session_state.report = report
            st.session_state.data = data
            st.session_state.sample_id = 0

            st.write(f"eval_name: {st.session_state.spec['eval_name']}")
            st.write(f"run_id: {st.session_state.spec['run_id']}")
            # write report in json format
            st.write(st.session_state.report)


    with col2:
        # add both number input and slider to display each data
        if "data" in st.session_state:
            data = st.session_state.data
            col3, col4 = st.columns([1, 4])

            with col3:
                sample_id_input = st.number_input("sample_id", 1, len(data), value=st.session_state.sample_id + 1)
                if sample_id_input != st.session_state.sample_id + 1:
                    st.session_state.sample_id = sample_id_input - 1

            with col4:
                sample_id_slider = st.slider("slider", 1, len(data), value=st.session_state.sample_id + 1)
                if sample_id_slider != st.session_state.sample_id + 1:
                    st.session_state.sample_id = sample_id_slider - 1

            st.write(data[st.session_state.sample_id]["sample_id"])
            st.write(data[st.session_state.sample_id]["data"])


if __name__ == "__main__":
    main()