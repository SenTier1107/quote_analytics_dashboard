---
title: Quote Analytics Dashboard
colorFrom: red
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# 📊 명언 분석 · 추천 대시보드

> quotes.toscrape.com의 명언 데이터를 수집·분석·추천하는 FastAPI + Gradio 대시보드

## 🔗 배포 URL
- **대시보드**: https://sentier2006-quote-analytics-dashboard.hf.space/dashboard
- **Swagger API 문서**: https://sentier2006-quote-analytics-dashboard.hf.space/docs

---

## 📋 프로젝트 개요

`quotes.toscrape.com`에서 명언 데이터를 크롤링하여 SQLite에 저장하고,
FastAPI 기반 CRUD API와 Gradio 대시보드를 통해 데이터를 관리·분석·추천하는 시스템입니다.

데이터 흐름: 크롤링 → SQLite 저장 → FastAPI API → Gradio UI → 분석/추천

---

## ⚙️ 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | FastAPI, SQLite3 |
| 프론트엔드 | Gradio |
| 크롤링 | BeautifulSoup4, httpx |
| 분석 | scikit-learn (TF-IDF), sentence-transformers |
| 시각화 | matplotlib, wordcloud, networkx |
| 배포 | Docker, Hugging Face Spaces |

---

## 🚀 주요 기능

### 1. 데이터 수집
- quotes.toscrape.com에서 명언, 저자, 태그 크롤링 (100개+)
- Wikipedia API로 저자 메타데이터 수집 (생몰년, 직업, 소개)

### 2. CRUD API (FastAPI)
- 명언 추가 / 조회 / 수정 / 삭제
- Swagger UI (/docs)에서 API 명세 확인 가능

### 3. 시각화 분석
- 단어 빈도 막대그래프
- 전체 워드클라우드
- 명언 길이 분포 히스토그램
- 태그 빈도 분석

### 4. 저자 프로필
- Wikipedia 메타데이터 (사진, 생몰년, 직업, 소개)
- TF-IDF 기반 시그니처 단어 추출
- 저자별 주요 태그 분석

### 5. 다차원 분석
- 시대별 / 직업별 명언 수 분석
- 직업 그룹별 TF-IDF 시그니처 단어
- 태그 동시출현 네트워크 그래프

### 6. 취향 분석 · 추천
- 즐겨찾기 기반 취향 프로필 분석
- 규칙 기반 추천 (태그/저자/단어 매칭)
- 임베딩 기반 의미 추천 (sentence-transformers)

---

## 📁 프로젝트 구조

analyzers/      TF-IDF, 유사도, 네트워크 분석
api/            FastAPI 라우터 (CRUD)
core/           DB 연결, 모델, 설정
crawler/        크롤러, Wikipedia 수집
scripts/        시드 스크립트, 임베딩 생성
ui/             Gradio 대시보드
visualizers/    차트, 워드클라우드, 네트워크
main.py         FastAPI + Gradio 진입점
Dockerfile      HF Spaces 배포 설정
requirements.txt

---

## 🛠️ 로컬 실행 방법

1. 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate

2. 의존성 설치
pip install -r requirements.txt

3. 데이터 수집
python scripts/seed.py
python scripts/seed_authors.py
python scripts/build_embeddings.py

4. 서버 실행
uvicorn main:app --reload

접속
- 대시보드: http://127.0.0.1:8000/dashboard
- Swagger: http://127.0.0.1:8000/docs