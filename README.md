# 🍬 CandyData — HR AI Platform

**CandyData** is a next-generation HR AI platform that automates candidate search, screening, and interviewing.  
Seamlessly integrated with [hh.kz](https://hh.kz), CandyData leverages artificial intelligence to find the best candidates and conducts initial interviews using cutting-edge voice and video technologies.

---

## 🚀 Features

- **Candidate Search on hh.kz:**  
  Automatic parsing of resumes and job postings based on specified criteria.

- **AI-Powered Screening:**  
  Uses OpenAI models to analyze and match resumes with job requirements.

- **Automated Interviews:**
  - **Whisper:** Converts and analyzes speech from candidates during voice interviews.
  - **HeyGen:** Creates realistic video interviews with AI avatars for an engaging candidate experience.

- **Smart Data Storage:**  
  All candidates and job postings are embedded as vectors using Pinecone, enabling fast and accurate matching.

---

## 🛠️ Technologies Used

- [OpenAI](https://openai.com/) — resume parsing, screening, and analysis
- [Pinecone](https://www.pinecone.io/) — vector database for intelligent search and matching
- [Whisper](https://openai.com/research/whisper) — AI-powered speech recognition for interviews
- [HeyGen](https://www.heygen.com/) — video avatars for automated interview sessions
- Custom parsers for [hh.kz](https://hh.kz) — automated data collection and recruitment insight

---

## 📝 How It Works

1. HR specialist adds a job description or search criteria.
2. CandyData crawls hh.kz and finds matching candidates.
3. Invitations for automated interviews are sent to candidates.
4. Interviews are conducted via audio (Whisper) or video (HeyGen) agents.
5. All data and results are embedded for further AI-driven analysis and efficient shortlist generation.
