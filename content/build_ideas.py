"""주제 35개 x 세부 글감 305개 x 포맷 8개 = 글감 2440개 -> xlsx / md"""
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).parent))
from ideas_data import TOPICS  # noqa: E402


def has_batchim(word):
    ch = word.rstrip(" ?")[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28
    return ch in "0123456789LMNRlmnr" and 1 or 0


def josa(word, with_b, without_b):
    b = has_batchim(word)
    if with_b == "으로":
        return "로" if b in (0, 8) else "으로"  # ㄹ받침은 '로'
    return with_b if b else without_b


def noun(x):
    x = x.removesuffix("이란")
    return x.rstrip("?") + " 속설" if x.endswith("?") else x


FORMATS = [
    ("실전 팁", "릴스", ["{x}, 집에서 바로 따라 하는 3단계", "디자이너가 알려주는 {x} 실전 순서",
                         "5분이면 이해되는 {x} 가이드", "{x}, 이것 하나만 바꿔도 달라져요"]),
    ("동기부여 스토리", "릴스", ["{x} 고민하던 고객님이 달라진 날", "망설이던 {x}, 용기 내고 생긴 변화",
                                "{x}{ro} 자신감을 되찾은 고객 이야기", "처음엔 걱정했던 {x}, 지금은 추천하는 이유"]),
    ("원리 분석", "캐러셀", ["{x}, 왜 그렇게 될까? 원리 해설", "{x} 결과를 좌우하는 진짜 변수",
                            "디자이너가 {x} 전에 꼭 보는 3가지와 그 이유", "{x}{i} 사람마다 다르게 나오는 이유"]),
    ("통념 깨기", "릴스", ["{x}, 다들 잘못 알고 있는 한 가지", "{x}, 무조건 좋은 건 아닙니다",
                          "흔한 {x} 조언, 이제 그만 따라 하세요", "{x}에 정답이 하나라는 착각"]),
    ("관찰·트렌드", "스토리", ["요즘 부쩍 늘어난 {x} 문의, 이유는?", "고객님들이 잘 말하지 않는 {x}의 진짜 고민",
                              "디자이너 눈에만 보이는 {x}의 작은 차이", "요즘 고객님들이 {x}에서 가장 신경 쓰는 것"]),
    ("A vs B 비교", "캐러셀", ["{vs}, 나에게 맞는 건?", "{vs}, 뭐가 다를까?",
                              "{vs} 한 번에 정리", "{vs} 고민, 이 기준으로 끝내세요"]),
    ("현재 vs 미래", "피드", ["{x}, 지금과 1년 뒤는 이렇게 달라져요", "{x}의 오늘과 내일: 앞으로 바뀔 것",
                             "지금 {x}{eul} 챙기면 6개월 뒤 머릿결은?", "{x}, 내년엔 이렇게 바뀝니다"]),
    ("리스트", "캐러셀", ["{x}에서 흔한 실수 5가지", "{x} 전 체크리스트 7가지",
                         "{x}, 가장 많이 받는 질문 TOP 5", "디자이너 추천 {x} 꿀팁 5가지"]),
]


def headline(sub_idx, f_idx, x, vs):
    tpl = FORMATS[f_idx][2][(sub_idx + f_idx) % 4]
    n = noun(x)
    return tpl.format(x=n, vs=vs, ro=josa(n, "으로", "로"), i=josa(n, "이", "가"), eul=josa(n, "을", "를"))


def rows():
    out, sub_idx = [], 0
    for t_no, (topic, subs) in enumerate(TOPICS, 1):
        for x, vs in subs:
            for f_idx, (fmt, channel, _) in enumerate(FORMATS):
                ch = "릴스" if topic.startswith("시술 전후") else channel
                out.append((t_no, topic, x, fmt, headline(sub_idx, f_idx, x, vs), ch))
            sub_idx += 1
    return out


def build_xlsx(data, path):
    wb = Workbook()
    base = Font(name="Arial", size=10)
    head = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="2D2824")
    wrap = Alignment(vertical="top", wrap_text=True)

    def header(ws, cols, widths):
        for c, (name, w) in enumerate(zip(cols, widths), 1):
            cell = ws.cell(1, c, name)
            cell.font, cell.fill = head, fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(c)].width = w
        ws.freeze_panes = "A2"

    # 1) 전체 글감
    ws = wb.active
    ws.title = "전체 글감"
    header(ws, ["No", "주제 No", "주제", "세부 글감", "포맷", "글감 제목", "추천 형식", "상태", "게시일"],
           [7, 8, 20, 24, 14, 48, 10, 11, 12])
    for i, r in enumerate(data, 1):
        for c, v in enumerate((i,) + r, 1):
            ws.cell(i + 1, c, v).font = base
        ws.cell(i + 1, 8, "아이디어").font = base
    dv = DataValidation(type="list", formula1='"아이디어,작성중,촬영완료,게시완료"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"H2:H{len(data) + 1}")
    ws.auto_filter.ref = f"A1:I{len(data) + 1}"

    # 2) 매트릭스 (세부 글감 x 포맷)
    wm = wb.create_sheet("매트릭스")
    header(wm, ["주제", "세부 글감"] + [f[0] for f in FORMATS], [18, 22] + [34] * 8)
    for k in range(0, len(data), 8):
        chunk = data[k:k + 8]
        r = k // 8 + 2
        wm.cell(r, 1, chunk[0][1]).font = base
        wm.cell(r, 2, chunk[0][2]).font = base
        for j, row in enumerate(chunk):
            c = wm.cell(r, 3 + j, row[4])
            c.font, c.alignment = base, wrap

    # 3) 주제 목록 (글감 수는 수식으로 집계)
    wt = wb.create_sheet("주제 목록", 0)
    header(wt, ["No", "주제", "세부 글감 수", "글감 수", "게시완료"], [7, 26, 13, 10, 10])
    last = len(data) + 1
    for i, (topic, subs) in enumerate(TOPICS, 1):
        r = i + 1
        wt.cell(r, 1, i).font = base
        wt.cell(r, 2, topic).font = base
        wt.cell(r, 3, f"=COUNTIFS('매트릭스'!$A$2:$A$400,B{r})").font = base
        wt.cell(r, 4, f"=COUNTIFS('전체 글감'!$C$2:$C${last},B{r})").font = base
        wt.cell(r, 5, f"=COUNTIFS('전체 글감'!$C$2:$C${last},B{r},'전체 글감'!$H$2:$H${last},\"게시완료\")").font = base
    t = len(TOPICS) + 2
    wt.cell(t, 2, "합계").font = Font(name="Arial", size=10, bold=True)
    for col in "CDE":
        wt[f"{col}{t}"] = f"=SUM({col}2:{col}{t - 1})"
        wt[f"{col}{t}"].font = Font(name="Arial", size=10, bold=True)
    wt.cell(t + 2, 2, "사용법: '전체 글감' 탭의 상태(H열)를 바꾸면 게시완료 수가 자동 집계돼요.").font = base
    wt.cell(t + 3, 2, "매장 정보(AI 진단, OC 탈색, 배곧, 네이버 20%, 첫 방문 30~40%)는 사장님이 알려주신 내용이에요.").font = base
    wb.save(path)


def build_md(data, path):
    lines = [f"# 보그헤어아뜰리에 배곧점 콘텐츠 매트릭스 ({date.today()})", "",
             f"주제 {len(TOPICS)}개, 세부 글감 {len(data) // 8}개, 글감 {len(data)}개", ""]
    cols = [f[0] for f in FORMATS]
    for t_no, (topic, subs) in enumerate(TOPICS, 1):
        lines += [f"## {t_no}. {topic}", "", "| 세부 글감 | " + " | ".join(cols) + " |",
                  "|---" * (len(cols) + 1) + "|"]
        for r in [d for d in data if d[0] == t_no][::8]:
            idx = data.index(r)
            lines.append(f"| {r[2]} | " + " | ".join(d[4] for d in data[idx:idx + 8]) + " |")
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    out = Path(__file__).parent
    data = rows()
    assert len(data) == 2440, len(data)
    assert len({d[4] for d in data}) == len(data), "중복 제목 있음"
    build_xlsx(data, out / "voghair_content_ideas_2440.xlsx")
    build_md(data, out / f"content-matrix-{date.today()}.md")
    print(len(TOPICS), len(data))
