import altair as alt
import pandas as pd
import streamlit as st

# 브라우저 탭에 표시될 제목과 아이콘 (layout="wide"는 화면을 넓게 사용)
st.set_page_config(page_title="학생 성적 분석", page_icon="📊", layout="wide")

# -----------------------------------------------------------------------------
# 기본 설정: 열 이름과 한글 이름, 색상

# 점수 열
SCORE_COLS = {
    "math score": "수학",
    "reading score": "읽기",
    "writing score": "쓰기",
}

# 학생 특성(범주형) 열
CATEGORY_COLS = {
    "gender": "성별",
    "race/ethnicity": "인종/민족 그룹",
    "parental level of education": "부모 학력",
    "lunch": "점심 유형",
    "test preparation course": "시험 준비 과정",
}

# 부모 학력은 알파벳 순서보다 학력 순서로 보여주는 것이 자연스러움
EDUCATION_ORDER = [
    "some high school",
    "high school",
    "some college",
    "associate's degree",
    "bachelor's degree",
    "master's degree",
]

# 그룹을 구분할 때 사용하는 색상 (항상 같은 순서로 사용)
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
BAR_COLOR = SERIES_COLORS[0]
MEAN_COLOR = SERIES_COLORS[1]


def label(col):
    """열 이름을 한글 이름으로 바꿔줌"""
    names = {**SCORE_COLS, **CATEGORY_COLS, "average score": "종합"}
    return names.get(col, col)


def josa(word, with_final, without_final):
    """받침 유무에 따라 알맞은 조사를 붙여줌 (예: 수학은 / 읽기는)"""
    code = ord(word[-1]) - 0xAC00
    has_final = 0 <= code <= 11171 and code % 28 != 0
    return word + (with_final if has_final else without_final)


def category_order(df, col):
    """그룹을 보여줄 순서를 정함"""
    values = df[col].dropna().unique().tolist()
    if col == "parental level of education":
        ordered = [v for v in EDUCATION_ORDER if v in values]
        return ordered + sorted(v for v in values if v not in ordered)
    return sorted(values)


def color_scale(order):
    """그룹마다 고정된 색을 지정"""
    return alt.Scale(domain=order, range=SERIES_COLORS[: len(order)])


def corr_strength(r):
    """상관계수 크기를 말로 설명"""
    size = abs(r)
    if size >= 0.7:
        strength = "강한"
    elif size >= 0.4:
        strength = "중간 정도의"
    elif size >= 0.2:
        strength = "약한"
    else:
        return "거의 관계가 없음"
    direction = "양(+)의" if r > 0 else "음(-)의"
    return f"{strength} {direction} 상관관계"


def factor_gaps(df, subjects):
    """요인(범주형 열)마다 그룹 간 평균 점수 차이를 계산"""
    rows = []
    for cat in CATEGORY_COLS:
        for subject in subjects:
            means = df.groupby(cat)[subject].mean()
            rows.append(
                {
                    "요인": label(cat),
                    "과목": label(subject),
                    "점수 차이": round(means.max() - means.min(), 1),
                    "최고 그룹": means.idxmax(),
                    "최고 평균": round(means.max(), 1),
                    "최저 그룹": means.idxmin(),
                    "최저 평균": round(means.min(), 1),
                }
            )
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# 1. 파일 업로드

st.title("📊 학생 성적 데이터 분석")
st.write("`StudentsPerformance.csv` 파일을 아래 영역에 드래그 앤 드롭하세요.")

uploaded_file = st.file_uploader("CSV 파일 업로드", type="csv")

# 파일을 아직 올리지 않았으면 여기서 멈춤
if uploaded_file is None:
    st.info("파일을 업로드하면 분석 결과가 나타납니다.")
    st.stop()

df = pd.read_csv(uploaded_file)

# 필요한 열이 모두 있는지 확인
missing = [col for col in [*SCORE_COLS, *CATEGORY_COLS] if col not in df.columns]
if missing:
    st.error(f"다음 열을 찾을 수 없습니다: {', '.join(missing)}. StudentsPerformance.csv 파일이 맞는지 확인해 주세요.")
    st.stop()

# 세 과목의 평균 점수 열을 새로 만듦
df["average score"] = df[list(SCORE_COLS)].mean(axis=1).round(1)
ALL_SCORES = [*SCORE_COLS, "average score"]

with st.expander("데이터 미리보기"):
    st.write(f"전체 {len(df):,}행 × {len(df.columns)}열 (마지막 'average score'는 세 과목 평균으로 새로 만든 '종합' 점수 열)")
    st.dataframe(df.head(10))

# 화면을 탭으로 나눔
tab_summary, tab_basic, tab_subject, tab_group, tab_corr, tab_factor = st.tabs(
    ["📌 분석 요약", "📈 기초 통계", "📚 과목 비교", "👥 그룹별 비교", "🔗 상관관계", "🎯 영향 요인"]
)

# -----------------------------------------------------------------------------
# 탭 1. 분석 요약: 주요 결과를 자동으로 정리

with tab_summary:
    st.header("핵심 분석 결과", divider="gray")

    # 과목별 평균 점수 카드
    cols = st.columns(len(ALL_SCORES))
    for col, subject in zip(cols, ALL_SCORES):
        col.metric(f"{label(subject)} 평균", f"{df[subject].mean():.1f}점")

    findings = []

    # 1) 평균이 가장 높은/낮은 과목
    subject_means = df[list(SCORE_COLS)].mean()
    findings.append(
        f"**과목별 평균**: 가장 높은 과목은 **{label(subject_means.idxmax())}**({subject_means.max():.1f}점), "
        f"가장 낮은 과목은 **{label(subject_means.idxmin())}**({subject_means.min():.1f}점)입니다."
    )

    # 2) 평균 점수에 가장 큰 영향을 주는 요인
    gaps = factor_gaps(df, ["average score"]).sort_values("점수 차이", ascending=False)
    top = gaps.iloc[0]
    findings.append(
        f"**가장 큰 영향 요인**: **{top['요인']}**에 따라 평균 점수가 가장 크게 달라집니다. "
        f"'{top['최고 그룹']}' 그룹({top['최고 평균']}점)이 '{top['최저 그룹']}' 그룹({top['최저 평균']}점)보다 "
        f"**{top['점수 차이']}점** 높습니다."
    )

    # 3) 성별에 따른 과목별 차이
    gender_means = df.groupby("gender")[list(SCORE_COLS)].mean()
    gender_parts = []
    for subject in SCORE_COLS:
        best = gender_means[subject].idxmax()
        diff = gender_means[subject].max() - gender_means[subject].min()
        gender_parts.append(f"{label(subject)}: {best} 쪽이 {diff:.1f}점 높음")
    findings.append("**성별 차이**: " + ", ".join(gender_parts) + ".")

    # 4) 시험 준비 과정의 효과
    prep_means = df.groupby("test preparation course")["average score"].mean()
    if {"completed", "none"} <= set(prep_means.index):
        prep_diff = prep_means["completed"] - prep_means["none"]
        findings.append(
            f"**시험 준비 과정**: 준비 과정을 완료한 학생의 평균 점수가 그렇지 않은 학생보다 "
            f"**{abs(prep_diff):.1f}점** {'높습니다' if prep_diff > 0 else '낮습니다'}."
        )

    # 5) 가장 관련이 깊은 두 과목
    corr = df[list(SCORE_COLS)].corr()
    pairs = [
        (a, b, corr.loc[a, b])
        for i, a in enumerate(SCORE_COLS)
        for b in list(SCORE_COLS)[i + 1 :]
    ]
    a, b, r = max(pairs, key=lambda p: p[2])
    findings.append(
        f"**과목 간 관계**: **{josa(label(a), '과', '와')}** **{label(b)}** 점수의 상관계수는 {r:.2f}로 "
        f"{corr_strength(r)}입니다."
    )

    # 6) 모든 과목 60점 이상인 학생 비율
    all_pass = (df[list(SCORE_COLS)] >= 60).all(axis=1).mean() * 100
    findings.append(f"**60점 기준**: 세 과목 모두 60점 이상인 학생은 전체의 **{all_pass:.1f}%**입니다.")

    for finding in findings:
        st.markdown(f"- {finding}")

    st.caption("각 탭에서 더 자세한 차트와 표를 확인할 수 있습니다.")

# -----------------------------------------------------------------------------
# 탭 2. 기초 통계: 과목 하나를 골라 자세히 보기

with tab_basic:
    st.header("과목별 기초 통계", divider="gray")

    subject = st.selectbox("과목 선택", ALL_SCORES, format_func=label, key="basic_subject")
    scores = df[subject]

    # 주요 통계값을 카드 형태로 표시
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("학생 수", f"{scores.count():,}명")
    col2.metric("평균", f"{scores.mean():.1f}점")
    col3.metric("중앙값", f"{scores.median():.1f}점")
    col4.metric("표준편차", f"{scores.std():.1f}")
    col5.metric("최솟값", f"{scores.min()}점")
    col6.metric("최댓값", f"{scores.max()}점")

    left, right = st.columns(2)

    # 히스토그램: 점수가 어떻게 분포되어 있는지
    with left:
        st.subheader("점수 분포 (히스토그램)")
        bin_size = st.slider("구간 크기 (점)", min_value=2, max_value=20, value=5)

        histogram = (
            alt.Chart(df)
            .mark_bar(color=BAR_COLOR, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X(f"{subject}:Q", bin=alt.Bin(step=bin_size), title=f"{label(subject)} 점수"),
                y=alt.Y("count():Q", title="학생 수"),
                tooltip=[
                    alt.Tooltip(f"{subject}:Q", bin=alt.Bin(step=bin_size), title="점수 구간"),
                    alt.Tooltip("count():Q", title="학생 수"),
                ],
            )
        )
        # 평균 위치를 세로 점선으로 표시
        mean_line = (
            alt.Chart(pd.DataFrame({"평균": [scores.mean()]}))
            .mark_rule(color=MEAN_COLOR, strokeWidth=2, strokeDash=[6, 4])
            .encode(x="평균:Q", tooltip=alt.Tooltip("평균:Q", format=".1f"))
        )
        st.altair_chart(histogram + mean_line, width="stretch")
        st.caption(f"주황색 점선은 평균({scores.mean():.1f}점)입니다.")

    # 박스 플롯: 사분위수와 이상치 확인
    with right:
        st.subheader("사분위수 (박스 플롯)")
        box_plot = (
            alt.Chart(df)
            .mark_boxplot(color=BAR_COLOR, size=40, extent=1.5)
            .encode(x=alt.X(f"{subject}:Q", title=f"{label(subject)} 점수"))
            .properties(height=150)
        )
        st.altair_chart(box_plot, width="stretch")
        st.caption("상자는 1사분위수(25%)~3사분위수(75%) 구간, 가운데 선은 중앙값, 바깥의 점은 이상치입니다.")

        # 기준 점수 이상인 학생 비율
        st.subheader("기준 점수 이상 비율")
        cutoff = st.slider("기준 점수", min_value=0, max_value=100, value=60, key="cutoff")
        above = (scores >= cutoff).mean() * 100
        st.metric(f"{cutoff}점 이상인 학생", f"{above:.1f}%", f"{(scores >= cutoff).sum():,}명", delta_color="off")

    # 통계 요약 표와 분석 결과
    st.subheader("통계 요약 표")
    summary = scores.describe().rename(
        {
            "count": "개수",
            "mean": "평균",
            "std": "표준편차",
            "min": "최솟값",
            "25%": "1사분위수 (25%)",
            "50%": "중앙값 (50%)",
            "75%": "3사분위수 (75%)",
            "max": "최댓값",
        }
    )
    st.dataframe(summary.round(2).to_frame(label(subject)))

    q1, q3 = scores.quantile(0.25), scores.quantile(0.75)
    skew = scores.skew()
    if skew < -0.2:
        shape = "낮은 점수 쪽으로 꼬리가 긴(왼쪽으로 치우친)"
    elif skew > 0.2:
        shape = "높은 점수 쪽으로 꼬리가 긴(오른쪽으로 치우친)"
    else:
        shape = "대체로 좌우 대칭인"
    st.info(
        f"**분석 결과**: {label(subject)} 점수는 평균 {scores.mean():.1f}점, 중앙값 {scores.median():.1f}점입니다. "
        f"학생 절반이 {q1:.0f}점~{q3:.0f}점 사이에 있으며, 분포는 {shape} 모양입니다 (왜도 {skew:.2f})."
    )

# -----------------------------------------------------------------------------
# 탭 3. 과목 비교: 세 과목을 한 화면에서 비교

with tab_subject:
    st.header("세 과목 점수 비교", divider="gray")

    # 차트를 그리기 위해 '과목', '점수' 두 열로 데이터 모양을 바꿈
    long_df = df[list(SCORE_COLS)].melt(var_name="과목", value_name="점수")
    long_df["과목"] = long_df["과목"].map(label)
    subject_order = list(SCORE_COLS.values())

    left, right = st.columns(2)

    with left:
        st.subheader("과목별 점수 분포 (박스 플롯)")
        box = (
            alt.Chart(long_df)
            .mark_boxplot(size=50, extent=1.5)
            .encode(
                x=alt.X("과목:N", sort=subject_order, title=None),
                y=alt.Y("점수:Q", title="점수"),
                color=alt.Color("과목:N", scale=color_scale(subject_order), legend=None),
            )
        )
        st.altair_chart(box, width="stretch")

    with right:
        st.subheader("과목별 점수 분포 (밀도 곡선)")
        density = (
            alt.Chart(long_df)
            .transform_density("점수", groupby=["과목"], as_=["점수", "밀도"], extent=[0, 100])
            .mark_line(strokeWidth=2)
            .encode(
                x=alt.X("점수:Q", title="점수"),
                y=alt.Y("밀도:Q", title="밀도"),
                color=alt.Color("과목:N", scale=color_scale(subject_order), legend=alt.Legend(orient="top")),
                tooltip=["과목:N", alt.Tooltip("점수:Q", format=".0f")],
            )
        )
        st.altair_chart(density, width="stretch")
        st.caption("밀도 곡선은 히스토그램을 부드럽게 이은 선입니다. 봉우리가 있는 곳에 학생이 많습니다.")

    st.subheader("과목별 통계 비교표")
    compare = df[list(SCORE_COLS)].agg(["mean", "median", "std", "min", "max"]).T
    compare.columns = ["평균", "중앙값", "표준편차", "최솟값", "최댓값"]
    compare.index = [label(c) for c in compare.index]
    st.dataframe(compare.round(1))

    spread = compare["표준편차"]
    st.info(
        f"**분석 결과**: 평균은 **{josa(compare['평균'].idxmax(), '이', '가')}** 가장 높고 "
        f"**{josa(compare['평균'].idxmin(), '이', '가')}** 가장 낮습니다. "
        f"점수가 가장 넓게 퍼진 과목(표준편차가 큰 과목)은 **{spread.idxmax()}**({spread.max():.1f})입니다."
    )

# -----------------------------------------------------------------------------
# 탭 4. 그룹별 비교: 학생 특성에 따라 점수가 어떻게 다른지

with tab_group:
    st.header("학생 특성별 점수 비교", divider="gray")

    col1, col2 = st.columns(2)
    factor = col1.selectbox("비교할 특성", list(CATEGORY_COLS), format_func=label)
    subject = col2.selectbox("과목", ALL_SCORES, format_func=label, key="group_subject")

    order = category_order(df, factor)
    stats = (
        df.groupby(factor)[subject]
        .agg(["count", "mean", "median", "std", "min", "max"])
        .reindex(order)
        .reset_index()
    )
    stats.columns = [factor, "학생 수", "평균", "중앙값", "표준편차", "최솟값", "최댓값"]

    left, right = st.columns(2)

    with left:
        st.subheader("그룹별 평균 점수")
        bars = (
            alt.Chart(stats)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X(f"{factor}:N", sort=order, title=None, axis=alt.Axis(labelAngle=-30)),
                y=alt.Y("평균:Q", title=f"{label(subject)} 평균 점수"),
                color=alt.Color(f"{factor}:N", scale=color_scale(order), legend=None),
                tooltip=[
                    alt.Tooltip(f"{factor}:N", title=label(factor)),
                    alt.Tooltip("평균:Q", format=".1f"),
                    alt.Tooltip("학생 수:Q"),
                ],
            )
        )
        bar_labels = bars.mark_text(dy=-8).encode(
            text=alt.Text("평균:Q", format=".1f"), color=alt.value("gray")
        )
        st.altair_chart(bars + bar_labels, width="stretch")

    with right:
        st.subheader("그룹별 점수 분포")
        group_box = (
            alt.Chart(df)
            .mark_boxplot(size=35, extent=1.5)
            .encode(
                x=alt.X(f"{factor}:N", sort=order, title=None, axis=alt.Axis(labelAngle=-30)),
                y=alt.Y(f"{subject}:Q", title=f"{label(subject)} 점수"),
                color=alt.Color(f"{factor}:N", scale=color_scale(order), legend=None),
            )
        )
        st.altair_chart(group_box, width="stretch")

    st.subheader("그룹별 통계표")
    st.dataframe(stats.round(1), hide_index=True)

    best = stats.loc[stats["평균"].idxmax()]
    worst = stats.loc[stats["평균"].idxmin()]
    overall = df[subject].mean()
    st.info(
        f"**분석 결과**: {label(factor)}에 따라 {label(subject)} 평균 점수는 "
        f"'{best[factor]}' 그룹이 {best['평균']:.1f}점으로 가장 높고, "
        f"'{worst[factor]}' 그룹이 {worst['평균']:.1f}점으로 가장 낮아 **{best['평균'] - worst['평균']:.1f}점** 차이가 납니다. "
        f"(전체 평균 {overall:.1f}점)"
    )

# -----------------------------------------------------------------------------
# 탭 5. 상관관계: 과목 점수끼리 얼마나 관련 있는지

with tab_corr:
    st.header("과목 간 상관관계", divider="gray")
    st.write("상관계수는 -1~1 사이 값으로, 1에 가까울수록 '한 과목 점수가 높으면 다른 과목도 높다'는 뜻입니다.")

    left, right = st.columns(2)

    with left:
        st.subheader("상관계수 히트맵")
        corr = df[list(SCORE_COLS)].corr()
        corr_df = corr.rename(index=label, columns=label).reset_index(names="과목1").melt(
            id_vars="과목1", var_name="과목2", value_name="상관계수"
        )
        heat = (
            alt.Chart(corr_df)
            .mark_rect(stroke="white", strokeWidth=2)
            .encode(
                x=alt.X("과목1:N", sort=subject_order, title=None),
                y=alt.Y("과목2:N", sort=subject_order, title=None),
                color=alt.Color(
                    "상관계수:Q",
                    scale=alt.Scale(scheme="blueorange", domain=[-1, 1]),
                    legend=alt.Legend(title="상관계수"),
                ),
                tooltip=["과목1:N", "과목2:N", alt.Tooltip("상관계수:Q", format=".2f")],
            )
        )
        heat_text = heat.mark_text(fontSize=16).encode(
            text=alt.Text("상관계수:Q", format=".2f"),
            color=alt.value("black"),
        )
        st.altair_chart((heat + heat_text).properties(height=320), width="stretch")

    with right:
        st.subheader("산점도")
        c1, c2, c3 = st.columns(3)
        x_col = c1.selectbox("X축", list(SCORE_COLS), index=1, format_func=label)
        y_col = c2.selectbox("Y축", list(SCORE_COLS), index=0, format_func=label)
        color_by = c3.selectbox("색으로 구분", ["(없음)", *CATEGORY_COLS], format_func=label)

        if color_by == "(없음)":
            point_color = alt.value(BAR_COLOR)
        else:
            point_color = alt.Color(
                f"{color_by}:N",
                scale=color_scale(category_order(df, color_by)),
                legend=alt.Legend(title=label(color_by), orient="top"),
            )
        points = (
            alt.Chart(df)
            .mark_circle(size=40, opacity=0.6, stroke="white", strokeWidth=0.5)
            .encode(
                x=alt.X(f"{x_col}:Q", title=f"{label(x_col)} 점수"),
                y=alt.Y(f"{y_col}:Q", title=f"{label(y_col)} 점수"),
                color=point_color,
                tooltip=[*CATEGORY_COLS, *SCORE_COLS],
            )
        )
        # 전체 데이터의 추세선
        trend = (
            alt.Chart(df)
            .transform_regression(x_col, y_col)
            .mark_line(color="gray", strokeWidth=2, strokeDash=[6, 4])
            .encode(x=f"{x_col}:Q", y=f"{y_col}:Q")
        )
        st.altair_chart(points + trend, width="stretch")
        st.caption("회색 점선은 전체 데이터의 추세선(회귀선)입니다.")

    if x_col == y_col:
        st.warning("X축과 Y축에 서로 다른 과목을 선택해 주세요.")
    else:
        r = df[x_col].corr(df[y_col])
        st.info(
            f"**분석 결과**: {josa(label(x_col), '과', '와')} {label(y_col)} 점수의 상관계수는 **{r:.2f}**로 {corr_strength(r)}입니다. "
            f"{label(x_col)} 점수로 {label(y_col)} 점수 차이의 약 **{r ** 2 * 100:.0f}%**를 설명할 수 있습니다 "
            f"(결정계수 R² = {r ** 2:.2f})."
        )

# -----------------------------------------------------------------------------
# 탭 6. 영향 요인: 어떤 특성이 점수에 가장 큰 영향을 주는지

with tab_factor:
    st.header("점수에 영향을 주는 요인", divider="gray")
    st.write("각 특성에서 평균이 가장 높은 그룹과 가장 낮은 그룹의 점수 차이를 비교합니다. 차이가 클수록 영향이 큰 요인입니다.")

    gaps = factor_gaps(df, ALL_SCORES)
    ranking = gaps[gaps["과목"] == label("average score")].sort_values("점수 차이", ascending=False)
    factor_order = ranking["요인"].tolist()
    score_order = [label(s) for s in ALL_SCORES]

    st.subheader("요인 × 과목별 점수 차이 히트맵")
    gap_heat = (
        alt.Chart(gaps)
        .mark_rect(stroke="white", strokeWidth=2)
        .encode(
            x=alt.X("과목:N", sort=score_order, title=None, axis=alt.Axis(labelAngle=0, orient="top")),
            y=alt.Y("요인:N", sort=factor_order, title=None),
            color=alt.Color("점수 차이:Q", scale=alt.Scale(scheme="blues"), legend=alt.Legend(title="점수 차이")),
            tooltip=["요인:N", "과목:N", "점수 차이:Q", "최고 그룹:N", "최고 평균:Q", "최저 그룹:N", "최저 평균:Q"],
        )
    )
    gap_text = gap_heat.mark_text(fontSize=14).encode(
        text=alt.Text("점수 차이:Q", format=".1f"),
        color=alt.condition(
            alt.datum["점수 차이"] > gaps["점수 차이"].max() * 0.6, alt.value("white"), alt.value("black")
        ),
    )
    st.altair_chart((gap_heat + gap_text).properties(height=300), width="stretch")
    st.caption("칸에 마우스를 올리면 점수가 가장 높은 그룹과 가장 낮은 그룹을 볼 수 있습니다.")

    st.subheader("평균 점수 기준 영향 요인 순위")
    st.dataframe(ranking.drop(columns="과목"), hide_index=True)

    # 과목별로 가장 영향이 큰 요인
    lines = []
    for subject in SCORE_COLS:
        row = gaps[gaps["과목"] == label(subject)].sort_values("점수 차이", ascending=False).iloc[0]
        lines.append(f"{label(subject)}: **{row['요인']}** ({row['점수 차이']}점 차이)")
    st.info(
        f"**분석 결과**: 평균 점수에 가장 큰 영향을 주는 요인은 **{ranking.iloc[0]['요인']}**, "
        f"가장 작은 요인은 **{ranking.iloc[-1]['요인']}**입니다.  \n"
        f"과목별로 가장 영향이 큰 요인 → " + " / ".join(lines)
    )

    # 두 요인을 함께 보기
    st.subheader("두 요인을 함께 보기")
    c1, c2, c3 = st.columns(3)
    factor_a = c1.selectbox("요인 1", list(CATEGORY_COLS), index=4, format_func=label)
    factor_b = c2.selectbox("요인 2", list(CATEGORY_COLS), index=3, format_func=label)
    subject = c3.selectbox("과목", ALL_SCORES, index=3, format_func=label, key="two_factor_subject")

    if factor_a == factor_b:
        st.warning("서로 다른 두 요인을 선택해 주세요.")
    else:
        two = df.groupby([factor_a, factor_b])[subject].agg(["mean", "count"]).reset_index()
        two.columns = [factor_a, factor_b, "평균", "학생 수"]
        two_heat = (
            alt.Chart(two)
            .mark_rect(stroke="white", strokeWidth=2)
            .encode(
                x=alt.X(f"{factor_a}:N", sort=category_order(df, factor_a), title=label(factor_a)),
                y=alt.Y(f"{factor_b}:N", sort=category_order(df, factor_b), title=label(factor_b)),
                color=alt.Color("평균:Q", scale=alt.Scale(scheme="blues"), legend=alt.Legend(title="평균 점수")),
                tooltip=[
                    alt.Tooltip(f"{factor_a}:N", title=label(factor_a)),
                    alt.Tooltip(f"{factor_b}:N", title=label(factor_b)),
                    alt.Tooltip("평균:Q", format=".1f"),
                    "학생 수:Q",
                ],
            )
        )
        mid = (two["평균"].min() + two["평균"].max()) / 2
        two_text = two_heat.mark_text(fontSize=14).encode(
            text=alt.Text("평균:Q", format=".1f"),
            color=alt.condition(alt.datum["평균"] > mid, alt.value("white"), alt.value("black")),
        )
        st.altair_chart((two_heat + two_text).properties(height=300), width="stretch")

        best = two.loc[two["평균"].idxmax()]
        worst = two.loc[two["평균"].idxmin()]
        st.info(
            f"**분석 결과**: {label(subject)} 점수 평균이 가장 높은 조합은 '{best[factor_a]}' + '{best[factor_b]}' "
            f"({best['평균']:.1f}점, {best['학생 수']}명), 가장 낮은 조합은 '{worst[factor_a]}' + '{worst[factor_b]}' "
            f"({worst['평균']:.1f}점, {worst['학생 수']}명)으로 **{best['평균'] - worst['평균']:.1f}점** 차이가 납니다."
        )
