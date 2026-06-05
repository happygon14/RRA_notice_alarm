# [준비] (import / 환경변수 / session생성)
# 1-1. 라이브러리(도구)

  # 1) 기본 내장 라이브러리
import os                          # 운영체제(OS)기능 접근용 (파일존재확인, 환경변수읽기, 파일명처리 등)
import smtplib                     # 이메일 전송 (SMTP서버로 메일보내기)
import re                          # 문자패턴찾기 (게시글 제목 분석시)

  # 2) 웹 크롤링 계열
import requests                     # 웹사이트 접속(GET/POST)
from bs4 import BeautifulSoup       # HTML 분석
import cloudscraper                 # request강화버전 (차단 우회용) (일반 requests 막히는 경우)

  # 3) 접속 안정화
import urllib3                            # SSL경고 숨김
urllib3.disable_warnings()                # SSL경고메시지 숨김
from urllib3.util.retry import Retry      # 실패시 자동 재시도 (서버 일시오류 대응)
from requests.adapters import HTTPAdapter # requests 세션에 재시도 기능 연결

  # 4) 이메일 MIME계열
from email.mime.text import MIMEText            # 메일본문만들기
from email.mime.multipart import MIMEMultipart  # 본문+이미지+첨부파일 합체 
from email.mime.base import MIMEBase            # 엑셀/이미지 첨부
from email import encoders                      # 첨부파일 메일용 변환

# 1-2. 환경변수 
  # 1) 사이트 주소 (크롤링 대상 웹사이트)
LIST_URL = "https://www.rra.go.kr/ko/notice/atnList.do"    # 국립전파연구원 행정예고 목록페이지

  # 2) 이메일 환경변수 (Github Secret에 저장한 내용 불러오기)
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
TO_EMAIL = os.environ.get("TO_EMAIL")

  # 3) 웹사이트 접속용 브라우저(자동접속(봇) 차단 우회기능 강화버전_requests의 강화버전) & 안정적기능(retry등)
scraper = cloudscraper.create_scraper()        # create_scraper : 브라우저 하나 생성
session = requests.Session()                   # 연결유지하는 requests 객체생성(매번 새접속없이 연결 재사용)
retries = Retry(                               # 접속실패시 자동재시도
    total=5,                                        # 최대 5번
    backoff_factor=2,                               # 실패할수록 대기시간 2배씩 증가
    status_forcelist=[429,500,502,503,504],         # 이 오류코드 나오면 재시도 (429:너무많이 접속, 500:서버오류, 503:서버점검 등)
)
adapter = HTTPAdapter(max_retries=retries)     # requests에 retry 기능 장착

session.mount("https://", adapter)             # 모든 웹접속시 retry기능 적용
session.mount("http://", adapter)



# [기능 정의(def)]  1.공지찾기, 2.첨부찾기, 3.다운로드, 4.메일발송

# 2-1. 최신 공지찾기

def get_latest_notice():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Referer": "https://www.rra.go.kr/",
        "Accept-Language": "ko-KR,ko;q=0.9"
    }

    res = session.get(
        LIST_URL,
        headers=headers,
        timeout=(30, 60),
        verify=False
    )

    print("status =", res.status_code)

    soup = BeautifulSoup(res.text, "html.parser")

    rows = soup.select("table.table_organ0 tbody tr")

    for row in rows:

        a = row.select_one("a")

        if not a:
            continue

        status_tag = row.select_one("span")

        status = (
            status_tag.get_text(strip=True)
            if status_tag
            else ""
        )

        # 진행중만 대상
        if status != "진행중":
            continue

        href = a["href"]

        m = re.search(r"nb_seq=(\d+)", href)

        if not m:
            continue

        notice_id = m.group(1)

        title = a.get_text(" ", strip=True)
        title = title.replace(status, "", 1).strip()

        detail_url = "https://www.rra.go.kr" + href

        return notice_id, title, detail_url

    raise Exception("진행중 행정예고를 찾지 못함")



# =========================
# 메일 보내기 (첨부 포함)
# =========================

def send_email(title, link):

    msg = MIMEMultipart()

    msg["Subject"] = "[RRA 행정예고]"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL

    body = f"""
새로운 행정예고가 등록되었습니다.

제목:
{title}

링크:
{link}
"""

    msg.attach(
        MIMEText(body, "plain", "utf-8")
    )

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465
    ) as server:

        server.login(
            EMAIL_ADDRESS,
            EMAIL_PASSWORD
        )

        server.send_message(msg)

# =========================
# 메인
# =========================
def main():

    latest_id, title, link = get_latest_notice()

    if os.path.exists("last_id.txt"):

        with open("last_id.txt", "r") as f:
            old_id = f.read().strip()

    else:
        old_id = None

    print("현재 게시글:", latest_id)
    print("기존 게시글:", old_id)

    if latest_id != old_id:

        print("새 공지 발견")

        send_email(
            title,
            link
        )

        with open("last_id.txt", "w") as f:
            f.write(latest_id)

    else:

        print("변경 없음")


if __name__ == "__main__":
    main()
