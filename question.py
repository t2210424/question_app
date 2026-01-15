# http://192.168.0.249:8501/
# http://192.168.10.113:8501
# http://192.168.68.21:8501

import time
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

API_URL = "https://nonvibrating-unstatical-anna.ngrok-free.dev/api"

# 起動するコマンド　"streamlit run question.py"

# -----------------------------
# 質問定義（英語表記なし、各質問に補足付き）
# -----------------------------
QUESTIONS = [
    {"title": "1. 私は誰か？", "note": 
     "基本から始め，想像力で空白を埋めていきましょう．\n\n"
     "性別，年齢，職業などのプロフィール，自認の性格，他者の評価，そのギャップ，過去の重要な出来事など"
    },

    {"title": "2. 私はどこにいるのか？", "note": 
     "シーン中の行動を決定づける要素となりうる「場所」を決めていきましょう．\n\n"
     "国，町，場所，屋内か屋外か，親しみや思い入れのある場所か慣れない場所か，見えているものなど"
     },

    {"title": "3. 時はいつ？", "note": 
     "キャラクターの行動に影響を与える「時」を決めましょう．\n\n"
     "年，季節，月，日，時間帯など",
     "min_chars": 30},

    {"title": "4. 何がしたいのか？", "note": 
     "キャラクターがシーン内で行う全ての行動の根底にある「動機」を考えましょう．\n\n"
     "全ての行動は，シーン内の他のキャラクターから自分が望むものを得るという目標に向かって実行されるべきです．"
     "これはキャラクターの目的とも呼ばれます．"
     },

    {"title": "5. なぜそれを望むのか？", "note": 
     "キャラクターに行動する説得力のある理由を与えましょう．\n\n"
     "舞台やスクリーン上の目的には，必ず原動力となるものが必要であり，それがあなたの存在意義です．"
     "私たちには行動する理由があり，キャラクターも例外ではありません．"
     },

    {"title": "6. どうすれば望むことを達成できるか？", "note": 
     "目的を達成するための手段を考えましょう．\n\n"
     "対話や動き，身振りを使って他のキャラクターに影響を与える事ができます．"
     "これはキャラクターの戦術とも呼ばれます．"
     "一つの戦術が失敗した時のために，もう一つ戦術があると良いです．"
     },
     
    {"title": "7. 何を克服しなければならないか？", "note": 
     "目的を達成するにあたっての障壁を明らかにしましょう．\n\n"
     "通常，他の人物の目的や物理的な障害などの外部要因と本人の内面での葛藤が常に存在します．"
     },

    {
        "title": "8. あなたの演じる役になりきって，400字以内で自己紹介を書いてください．",
        "note": "「私は優しい性格です」のような直接的な性格説明は避け、話し言葉のような語尾やエピソードで人柄を伝えてください。"
        "「私の名前はヒナタ．」の後に続けてください。\n\n"
        "例：俺の名前はレン．朝は目覚ましが鳴る前に起きて，カーテンを勢いよく開け...",
        "min_chars": 200,
        "prefill": "私の名前はヒナタ．",
    },
]

import re

def count_chars_no_space_newline(text: str) -> int:
    # 半角/全角スペース、改行、タブなどの空白類を除外
    cleaned = re.sub(r"[ \u3000\r\n\t]", "", text)
    return len(cleaned)


st.set_page_config(page_title="Stanislavski 7 Questions Survey", layout="centered")

st.markdown(
    """
    <style>
      [data-testid="stSidebar"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)

# 画面内でスクロール先のアンカーを置いておく
st.markdown("<div id='top-anchor'></div>", unsafe_allow_html=True)

# 各ページ表示時にタイトル位置までスクロール（複数回試行）
st.components.v1.html(
    """
    <script>
      (() => {
        const selectors = ['#top-anchor', 'section.main h1', 'h1'];
        const maxAttempts = 20;
        let count = 0;
        const scrollFn = () => {
          count += 1;
          try {
            const doc = window.parent?.document || document;
            let target = null;
            for (const sel of selectors) {
              target = doc.querySelector(sel);
              if (target) break;
            }
            if (target && target.scrollIntoView) {
              target.scrollIntoView({behavior: 'auto', block: 'start'});
            } else {
              doc.documentElement.scrollTop = 0;
              doc.body.scrollTop = 0;
            }
          } catch (e) {
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
          }
          if (count >= maxAttempts) clearInterval(timer);
        };
        const timer = setInterval(scrollFn, 50);
      })();
    </script>
    """,
    height=1,
    width=1,
)

DEFAULT_MIN_CHAR_COUNT = 50


# -----------------------------
# セッション状態初期化
# -----------------------------
if "q_index" not in st.session_state:
    st.session_state.q_index = 0

if "start_time" not in st.session_state:
    st.session_state.start_time = None  # 現在の質問の開始時刻（epoch）

if "responses" not in st.session_state:
    # 各要素: dict(question_id, title, note, answer, char_count, time_sec, chars_per_sec, recorded_at)
    st.session_state.responses = []

if "participant_id" not in st.session_state:
    st.session_state.participant_id = ""

# -----------------------------
# サイドバー：設定
# -----------------------------
st.sidebar.header("設定")

st.session_state.participant_id = st.sidebar.text_input(
    "参加者ID（任意）",
    value=st.session_state.participant_id,
    placeholder="例：P001"
)

limit_mode = st.sidebar.radio(
    "文字数制限の方式",
    ["制限なし", "全質問に同じ制限", "質問ごとに制限"],
    index=1
)

global_limit = None
per_question_limits = [None] * len(QUESTIONS)

if limit_mode == "全質問に同じ制限":
    global_limit = st.sidebar.number_input("文字数上限（全質問共通）", min_value=50, value=400, step=10)
elif limit_mode == "質問ごとに制限":
    st.sidebar.caption("各質問の上限を設定（空欄＝制限なし）")
    for i, q in enumerate(QUESTIONS):
        per_question_limits[i] = st.sidebar.number_input(
            f"Q{i+1} 上限",
            min_value=50,
            value=400,
            step=10,
            key=f"limit_q_{i}"
        )

st.sidebar.divider()
st.sidebar.caption("※回答時間は「質問が表示された時刻」から「次へ」を押すまでで計測します。")

# -----------------------------
# ヘルパ：Excel生成
# -----------------------------
def make_excel_bytes(responses: list[dict]) -> bytes:
    df = pd.DataFrame(responses)

    # サマリ
    if df.empty:
        summary = pd.DataFrame([{
            "total_questions": 0,
            "total_chars": 0,
            "total_time_sec": 0,
            "overall_chars_per_sec": 0,
        }])
    else:
        total_chars = int(df["char_count"].sum())
        total_time = float(df["time_sec"].sum())
        overall_cps = (total_chars / total_time) if total_time > 0 else 0.0
        summary = pd.DataFrame([{
            "total_questions": len(df),
            "total_chars": total_chars,
            "total_time_sec": round(total_time, 3),
            "overall_chars_per_sec": round(overall_cps, 6),
        }])

    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="responses", index=False)
        summary.to_excel(writer, sheet_name="summary", index=False)
    return out.getvalue()

# -----------------------------
# UI本体
# -----------------------------
st.title("実験後アンケート")

q_index = st.session_state.q_index
total_q = len(QUESTIONS)

# 完了画面
if q_index >= total_q:
    st.success("全ての質問が完了しました。Excelをダウンロードできます。")

    if st.session_state.responses:
        df_show = pd.DataFrame(st.session_state.responses)
        st.subheader("記録プレビュー")
        st.dataframe(df_show, use_container_width=True)

        excel_bytes = make_excel_bytes(st.session_state.responses)
        filename = f"stanislavski_survey_{st.session_state.participant_id or 'anonymous'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        st.download_button(
            label="Excelをダウンロード（.xlsx）",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("記録がありません。")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("最初からやり直す"):
            st.session_state.q_index = 0
            st.session_state.start_time = None
            st.session_state.responses = []
            st.rerun()
    with col2:
        if st.button("直前の質問に戻る"):
            st.session_state.q_index = max(0, total_q - 1)
            # 戻る際は開始時刻をリセット（計測し直し）
            st.session_state.start_time = time.time()
            st.rerun()

    st.stop()

# 質問表示開始時刻をセット（初回表示時のみ）
if st.session_state.start_time is None:
    st.session_state.start_time = time.time()

question = QUESTIONS[q_index]
title = question["title"]
note = question["note"]
min_chars = int(question.get("min_chars", DEFAULT_MIN_CHAR_COUNT))
st.progress((q_index) / total_q, text=f"進捗：{q_index}/{total_q}")

st.subheader(title)
if note:
    st.caption(note)

# 文字数制限の決定
limit = None
if limit_mode == "全質問に同じ制限":
    limit = int(global_limit)
elif limit_mode == "質問ごとに制限":
    limit = int(per_question_limits[q_index]) if per_question_limits[q_index] is not None else None

if limit is None and limit_mode == "制限なし":
    st.caption("文字数制限：なし")
elif limit is None:
    st.caption("文字数制限：なし（この質問）")
else:
    st.caption(f"文字数制限：最大 {limit} 文字")
st.caption(f"最小文字数：{min_chars} 文字")

answer_key = f"answer_q_{q_index}"
stored_answer = st.session_state.get(answer_key, None)
if stored_answer is None:
    # 再訪時に記録済みの回答があれば復元する
    for rec in reversed(st.session_state.responses):
        if rec.get("question_number") == q_index + 1:
            stored_answer = rec.get("answer", "")
            break
default_text = stored_answer if stored_answer is not None else question.get("prefill", "")

with st.form(key=f"form_q_{q_index}", clear_on_submit=False):
    answer = st.text_area(
        "回答を入力してください（Ctrl+Enter / ⌘+Enter で反映）",
        value=default_text,
        height=220,
        placeholder="ここに入力…",
        key=answer_key
    )

    # ここを押した時（=送信した時）にだけ再実行が走り、文字数が更新される
    submitted = st.form_submit_button("文字数反映（Ctrl+Enter / ⌘+Enter）")

# フォーム送信があったときだけ、確定済みの answer を使ってカウント更新
char_count = count_chars_no_space_newline(st.session_state.get(answer_key, ""))

# 計測（画面には表示しない）
elapsed = time.time() - st.session_state.start_time

# 文字数だけは表示（不要ならこの2行も削除OK）
st.metric("文字数", char_count)

# 制限チェック
if char_count < min_chars:
    st.error(f"文字数が不足しています（{char_count} / {min_chars} 以上必要）。")
if limit is not None and char_count > limit:
    st.error(f"文字数が上限を超えています（{char_count} / {limit}）。上限内に収めてください。")

# 操作ボタン
colA, colB, colC = st.columns(3)

with colA:
    if st.button("戻る（前の質問）", disabled=(q_index == 0)):
        st.session_state.q_index = max(0, q_index - 1)
        # 戻る際は開始時刻をリセット（計測し直し）
        st.session_state.start_time = time.time()
        st.rerun()

with colB:
    if st.button("この質問をリセット"):
        st.session_state[answer_key] = ""
        st.session_state.start_time = time.time()
        st.rerun()
    # ページ最上部へのリンク
    st.markdown("[ページの上部へ移動](#top-anchor)")

with colC:
    next_disabled = (char_count < min_chars) or (limit is not None and char_count > limit)
    if st.button("次へ", disabled=next_disabled):
        end_time = time.time()
        time_sec = end_time - st.session_state.start_time
        cps = (char_count / time_sec) if time_sec > 0 else 0.0

        record = {
            "participant_id": st.session_state.participant_id or "anonymous",
            "question_number": q_index + 1,
            "question_title": title,
            "question_note": note,
            "answer": answer,
            "char_count": int(char_count),
            "time_sec": round(float(time_sec), 3),
            "chars_per_sec": round(float(cps), 6),
            "recorded_at": datetime.now().isoformat(timespec="seconds"),
            "char_limit": limit if limit is not None else ""
        }
        st.session_state.responses.append(record)

        # 次へ進む & 次質問の開始時刻を初期化
        st.session_state.q_index = q_index + 1
        st.session_state.start_time = None
        st.rerun()
