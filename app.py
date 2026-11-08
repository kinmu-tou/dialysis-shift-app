import datetime
import pandas as pd
import streamlit as st


# 簡易的な日本の祝日判定関数
def is_japanese_holiday(date_obj):
  y, m, d = date_obj.year, date_obj.month, date_obj.day
  fixed_holidays = [
      (1, 1),
      (2, 11),
      (2, 23),
      (4, 29),
      (5, 3),
      (5, 4),
      (5, 5),
      (8, 11),
      (11, 3),
      (11, 23),
  ]
  if (m, d) in fixed_holidays:
    return True
  if m == 3 and d == int(20.8431 + 0.242194 * (y - 1980)) - int(
      (y - 1980) / 4
  ):
    return True
  if m == 9 and d == int(23.2488 + 0.242194 * (y - 1980)) - int(
      (y - 1980) / 4
  ):
    return True
  return False


# カンマ区切りの希望日文字列をセット（整数型）に変換するヘルパー関数
def parse_hope_days(day_str):
  days = set()
  if not isinstance(day_str, str):
    return days
  for part in day_str.replace("，", ",").split(","):
    part = part.strip()
    if part.isdigit():
      days.add(int(part))
  return days


# ページの設定
st.set_page_config(
    page_title="透析センター勤務表自動作成システム", page_icon="🏥", layout="wide"
)

st.title("🏥 医療現場向け：透析センター勤務表自動作成・編集システム")
st.markdown(
    "多職種（技士・看護師・CA・事務など）のシフトを自動生成し、ブラウザ上でExcelのように編集・確認できます。"
)

# サイドバー：設定
st.sidebar.header("⚙️ 勤務表の設定")
year = st.sidebar.selectbox("年", [2026, 2027], index=0)
month = st.sidebar.selectbox(
    "月", list(range(1, 13)), index=datetime.date.today().month - 1
)

# スタッフデータの定義
if "staff_df" not in st.session_state:
  st.session_state.staff_df = pd.DataFrame({
      "スタッフ名": [
          "尾藤",
          "佐藤恵",
          "麻生",
          "清松",
          "伊藤",
          "佐藤香",
          "白石",
          "大下",
          "安部",
          "後藤",
          "衛藤",
          "中西",
          "藤竿",
          "戸次",
          "石川",
          "岡田",
          "薄田",
          "阿部",
          "矢野",
      ],
      "職種": [
          "技士",
          "技士",
          "技士",
          "技士",
          "技士",
          "技士",
          "技士",
          "技士",
          "技士",
          "技士",
          "看護師",
          "看護師",
          "看護師",
          "看護師",
          "看護師",
          "看護師",
          "CA",
          "CA",
          "事務",
      ],
      "希望休(Q)": [
          "3, 15",
          "10",
          "5",
          "1",
          "8",
          "14",
          "2",
          "9",
          "4",
          "11",
          "6",
          "7",
          "4",
          "12",
          "3",
          "15",
          "5",
          "10",
          "8",
      ],
      "希望休(Y)": [
          "20",
          "20",
          "18",
          "12",
          "22",
          "25",
          "16",
          "21",
          "19",
          "24",
          "17",
          "13",
          "26",
          "23",
          "20",
          "28",
          "15",
          "22",
          "19",
      ],
      "委員会": [
          "10",
          "15",
          "",
          "",
          "5",
          "",
          "",
          "",
          "12",
          "",
          "8",
          "",
          "",
          "20",
          "",
          "",
          "",
          "",
          "",
      ],
  })

st.subheader("👥 スタッフ一覧・希望休・委員会設定")
st.markdown(
    "スタッフの追加・削除や、**希望休(Q)**・**希望休(Y)**・**委員会**の日付（カンマ区切り）の編集が可能です。"
)
edited_staff_df = st.data_editor(
    st.session_state.staff_df, num_rows="dynamic", key="staff_editor"
)

# シフト自動生成ボタン
if st.button("🚀 勤務表を自動生成する", type="primary"):
  # 月の日数を取得
  if month == 2:
    days_in_month = 28
  elif month in [4, 6, 9, 11]:
    days_in_month = 30
  else:
    days_in_month = 31

  day_columns = [str(d) for d in range(1, days_in_month + 1)]

  # スタッフデータを取得
  staff_list = []
  for idx, row in edited_staff_df.iterrows():
    staff_list.append({
        "name": row["スタッフ名"],
        "job": row["職種"],
        "q_days": parse_hope_days(row.get("希望休(Q)", "")),
        "y_days": parse_hope_days(row.get("希望休(Y)", "")),
        "committee_days": parse_hope_days(row.get("委員会", "")),
        "original_idx": idx,
    })

  technicians = [s for s in staff_list if s["job"] == "技士"]
  nurses = [s for s in staff_list if s["job"] == "看護師"]
  cas = [s for s in staff_list if s["job"] == "CA"]
  others = [s for s in staff_list if s["job"] not in ["技士", "看護師", "CA"]]

  schedule_dict = {s["name"]: [] for s in staff_list}

  general_pattern = ["日", "夜", "明", "休", "日", "休"]
  last_late_day = {n["name"]: -99 for n in nurses}
  tech_last_late_day = {t["name"]: -99 for t in technicians}

  for d in range(1, days_in_month + 1):
    current_date = datetime.date(year, month, d)
    w = current_date.weekday()  # 0:月, 1:火, 2:水, 3:木, 4:金, 5:土, 6:日
    is_hol = is_japanese_holiday(current_date)

    # ==========================================
    # 1. 技士の処理（全10名）
    # ==========================================
    if w == 6:  # 日曜は全員休
      for t_staff in technicians:
        if d in t_staff["committee_days"]:
          s = "日"
        elif d in t_staff["q_days"]:
          s = "Q"
        elif d in t_staff["y_days"]:
          s = "Y"
        else:
          s = "休"
        schedule_dict[t_staff["name"]].append(s)
    else:
      t_count = len(technicians)
      tech_assignments = {t["name"]: None for t in technicians}

      for t in technicians:
        if d in t["committee_days"]:
          tech_assignments[t["name"]] = "working"

      for t in technicians:
        if tech_assignments[t["name"]] == "working":
          continue
        if d in t["q_days"]:
          tech_assignments[t["name"]] = "Q"
        elif d in t["y_days"]:
          tech_assignments[t["name"]] = "Y"

      # ★制約：尾藤と佐藤恵のどちらか1人は必ず出勤する
      if (
          tech_assignments.get("尾藤") in ["Q", "Y"]
          and tech_assignments.get("佐藤恵") in ["Q", "Y"]
      ):
        tech_assignments["佐藤恵"] = None

      # ★制約：白石と尾藤のどちらか1人は必ず出勤する
      if (
          tech_assignments.get("尾藤") in ["Q", "Y"]
          and tech_assignments.get("白石") in ["Q", "Y"]
      ):
        tech_assignments["白石"] = None

      target_off_count = 1
      if w in [0, 4]:
        target_off_count = 2
      elif w in [1, 3, 5]:
        target_off_count = 3

      current_off_count = sum(
          1 for v in tech_assignments.values() if v in ["Q", "Y"]
      )

      if current_off_count < target_off_count:
        for i in range(t_count):
          idx_target = (d * 2 + i) % t_count
          t_name = technicians[idx_target]["name"]
          if (
              d in technicians[idx_target]["committee_days"]
              or tech_assignments[t_name] is not None
          ):
            continue

          # 尾藤＆佐藤恵の同時休み防止
          if t_name == "尾藤" and tech_assignments.get("佐藤恵") in ["Q", "Y"]:
            continue
          if t_name == "佐藤恵" and tech_assignments.get("尾藤") in ["Q", "Y"]:
            continue

          # 尾藤＆白石の同時休み防止
          if t_name == "尾藤" and tech_assignments.get("白石") in ["Q", "Y"]:
            continue
          if t_name == "白石" and tech_assignments.get("尾藤") in ["Q", "Y"]:
            continue

          tech_assignments[t_name] = "Q"
          current_off_count += 1
          if current_off_count >= target_off_count:
            break

      working_techs = [
          t["name"]
          for t in technicians
          if tech_assignments[t["name"]] in [None, "working"]
      ]

      if working_techs:
        working_for_early1 = [
            name for name in working_techs if name != "清松"
        ]
        if not working_for_early1:
          working_for_early1 = working_techs

        early1_name = working_for_early1[(d + 0) % len(working_for_early1)]
        tech_assignments[early1_name] = "早1"
        working_techs.remove(early1_name)

        if w in [0, 2, 4]:  # 月・水・金
          working_for_early = [name for name in working_techs if name != "清松"]
          for _ in range(min(2, len(working_for_early))):
            if working_for_early:
              name = working_for_early.pop(0)
              tech_assignments[name] = "早"
              working_techs.remove(name)

          if working_techs:
            name = working_techs.pop(0)
            tech_assignments[name] = "早2"

          tech_available_for_late = [
              name
              for name in working_techs
              if name != "尾藤" and (d - tech_last_late_day[name]) >= 6
          ]
          if not tech_available_for_late:
            tech_available_for_late = [
                name for name in working_techs if name != "尾藤"
            ]

          chosen_lates = []
          if tech_available_for_late:
            n1 = tech_available_for_late.pop(0)
            chosen_lates.append((n1, "（遅）"))
            working_techs.remove(n1)
            tech_last_late_day[n1] = d

          tech_available_for_late2 = [
              name
              for name in working_techs
              if name != "尾藤" and (d - tech_last_late_day[name]) >= 6
          ]
          if not tech_available_for_late2:
            tech_available_for_late2 = [
                name for name in working_techs if name != "尾藤"
            ]

          for _ in range(2):
            if any(item[0] == "白石" for item in chosen_lates):
              cand2 = [n for n in tech_available_for_late2 if n != "後藤"]
            elif any(item[0] == "後藤" for item in chosen_lates):
              cand2 = [n for n in tech_available_for_late2 if n != "白石"]
            else:
              cand2 = tech_available_for_late2

            if cand2:
              n2 = cand2.pop(0)
              chosen_lates.append((n2, "遅"))
              if n2 in working_techs:
                working_techs.remove(n2)
              tech_last_late_day[n2] = d
              if n2 in tech_available_for_late2:
                tech_available_for_late2.remove(n2)

          for name, shift_type in chosen_lates:
            tech_assignments[name] = shift_type

          for name in working_techs:
            tech_assignments[name] = "日"

        elif w in [1, 3, 5]:  # 火・木・土
          for _ in range(min(2, len(working_techs))):
            if working_techs:
              name = working_techs.pop(0)
              tech_assignments[name] = "早2"
          for name in working_techs:
            tech_assignments[name] = "日"
        else:
          for name in working_techs:
            tech_assignments[name] = "日"

      for t in technicians:
        val = tech_assignments[t["name"]]
        if val in [None, "working"]:
          val = "日"
        schedule_dict[t["name"]].append(val)

    # ==========================================
    # 2. 看護師の処理 (6名)
    # ==========================================
    if w == 6:
      for n_staff in nurses:
        if d in n_staff["committee_days"]:
          s = "日"
        elif d in n_staff["q_days"]:
          s = "Q"
        elif d in n_staff["y_days"]:
          s = "Y"
        else:
          s = "休"
        schedule_dict[n_staff["name"]].append(s)
    else:
      n_count = len(nurses)
      q_idx = (d + 2) % n_count

      required_late_count = 2 if (w == 0 or w in [2, 4]) else 0
      required_early_count = 2 if w == 0 else (1 if w in [2, 4, 3] else 0)

      daily_assignments = {n["name"]: "日" for n in nurses}

      for n in nurses:
        if d in n["committee_days"]:
          daily_assignments[n["name"]] = "日"

      for n in nurses:
        if d in n["committee_days"]:
          continue
        if d in n["q_days"]:
          daily_assignments[n["name"]] = "Q"
        elif d in n["y_days"]:
          daily_assignments[n["name"]] = "Y"

      q_assigned_count = sum(
          1 for v in daily_assignments.values() if v == "Q"
      )
      if q_assigned_count == 0:
        candidate_idx = q_idx
        for _ in range(n_count):
          target_nurse = nurses[candidate_idx]
          if (
              d not in target_nurse["committee_days"]
              and d not in target_nurse["q_days"]
              and d not in target_nurse["y_days"]
          ):
            daily_assignments[target_nurse["name"]] = "Q"
            break
          candidate_idx = (candidate_idx + 1) % n_count

      available_for_late = []
      for n in nurses:
        name = n["name"]
        if d in n["committee_days"]:
          continue
        if daily_assignments[name] in ["Q", "Y"]:
          continue
        if name == "戸次":
          if (d - last_late_day[name]) >= 14:
            available_for_late.append(name)
        elif name == "中西":
          recent_lates = sum(
              1
              for past_d in range(max(1, d - 6), d)
              if schedule_dict[name]
              and len(schedule_dict[name]) >= past_d
              and schedule_dict[name][past_d - 1] == "遅"
          )
          if recent_lates < 2:
            available_for_late.append(name)
        else:
          recent_lates = sum(
              1
              for past_d in range(max(1, d - 6), d)
              if schedule_dict[name]
              and len(schedule_dict[name]) >= past_d
              and schedule_dict[name][past_d - 1] == "遅"
          )
          if recent_lates < 1:
            available_for_late.append(name)

      if len(available_for_late) < required_late_count:
        for n in nurses:
          name = n["name"]
          if (
              d not in n["committee_days"]
              and daily_assignments[name] not in ["Q", "Y"]
              and name not in available_for_late
          ):
            available_for_late.append(name)
            if len(available_for_late) >= required_late_count:
              break

      assigned_lates = 0
      for name in available_for_late:
        if assigned_lates < required_late_count:
          daily_assignments[name] = "遅"
          last_late_day[name] = d
          assigned_lates += 1

      available_for_early = [
          n["name"]
          for n in nurses
          if daily_assignments[n["name"]] == "日"
          and d not in n["committee_days"]
      ]
      assigned_earlies = 0
      for name in available_for_early:
        if assigned_earlies < required_early_count:
          daily_assignments[name] = "早"
          assigned_earlies += 1

      for n in nurses:
        schedule_dict[n["name"]].append(daily_assignments[n["name"]])

    # ==========================================
    # 3. CAの処理
    # ==========================================
    for c_staff in cas:
      if d in c_staff["committee_days"]:
        s = "日"
      elif d in c_staff["q_days"]:
        s = "Q"
      elif d in c_staff["y_days"]:
        s = "Y"
      elif w == 6:
        s = "休"
      else:
        if w in [0, 2, 4]:
          ca_sub = ["早", "遅"]
          s = ca_sub[(c_staff["original_idx"] + d) % len(ca_sub)]
        else:
          s = "日"
      schedule_dict[c_staff["name"]].append(s)

    # ==========================================
    # 4. その他（事務など）の処理
    # ==========================================
    for o_staff in others:
      if d in o_staff["committee_days"]:
        s = "Q" if (o_staff["job"] == "事務" and (w == 5 or is_hol)) else "日"
      elif d in o_staff["q_days"]:
        s = "Q"
      elif d in o_staff["y_days"]:
        s = "Y"
      elif w == 6:
        s = "休"
      else:
        if o_staff["job"] == "事務":
          if w == 5 or is_hol:
            s = "Q"
          else:
            s = general_pattern[
                (o_staff["original_idx"] + d) % len(general_pattern)
            ]
        else:
          s = general_pattern[
              (o_staff["original_idx"] + d) % len(general_pattern)
          ]
      schedule_dict[o_staff["name"]].append(s)

  # 最終的なテーブル形式に変換
  shift_data = []
  for s in staff_list:
    row_data = {"スタッフ名": s["name"], "職種": s["job"]}
    for i, d in enumerate(day_columns):
      row_data[d] = schedule_dict[s["name"]][i]
    shift_data.append(row_data)

  st.session_state.shift_df = pd.DataFrame(shift_data)
  st.success(
      f"🎉 {year}年{month}月の透析センター勤務表を自動生成しました！（白石と尾藤の出勤担保ルールを追加しました）"
  )

# 勤務表が生成されている場合の表示・編集エリア
if "shift_df" in st.session_state:
  st.markdown("---")
  st.subheader(
      f"📅 {year}年{month}月 度 透析センター勤務表（Excelのように編集可能）"
  )
  st.markdown("下の表のセルを直接クリックして、シフトを修正できます。")

  final_shift_df = st.data_editor(
      st.session_state.shift_df,
      key="shift_table_editor",
      use_container_width=True,
  )

  csv = final_shift_df.to_csv(index=False).encode("utf-8-sig")
  st.download_button(
      label="📥 透析センター勤務表をCSVでダウンロード",
      data=csv,
      file_name=f"dialysis_center_shift_{year}_{month}.csv",
      mime="text/csv",
  )