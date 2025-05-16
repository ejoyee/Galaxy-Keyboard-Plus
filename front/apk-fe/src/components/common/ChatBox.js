"use client";

import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import Image from "next/image";
import axiosInstance from "@/lib/axiosInstance";

// 전체 프롬프트 리스트
const ALL_PROMPTS = [
  "별 그려진 연두색 네일아트 사진 찾아줘",
  "하품하는 고양이 사진 좀",
  "이디야 와이파이 비밀번호 알아?",
  "봄봄 와이파이 비밀번호 알려줘",
  "오므라이스 네일아트 사진",
  "헬로키티 과자 사진 보내줘",
  "김해뒷고기 먹으러 언제 갔었지?",
  "ANTZ 와이파이 비밀번호가 뭐야?",
  "삼겹살 먹은 곳이 어디지?",
  "멸망인가 멸종인가 하는 시집 제목이 뭐더라?",
  "문상훈이 추천한 시집 제목",
  "편의점 기프티콘",
  "홍길동 씨 번호 좀 알려줘",
  "검은 수녀들 좌석 어디야",
  "파묘 어디서 봤었지?",
  "기생충 며칠에 봤었어?",
  "백두산 몇 명이서 봤지?",
  "피피티 만들 때 참고할만한 데가 어디였어",
  "해커톤 영남 본선 어디서 해?",
  "아이디어 경진대회 제출 마감일이 언제였지?",
  "프런티어 필수로 해야 하는 게 뭐였지?",
  "추천 고양이 사료",
  "오드아이 고양이 사진",
  "대구 간 날이 언제야?",
];

export default function ChatBox() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [availablePrompts, setAvailablePrompts] = useState(ALL_PROMPTS);
  const [visiblePrompts, setVisiblePrompts] = useState([]);
  const chatEndRef = useRef(null);
  const [isTyping, setIsTyping] = useState(false);

  // 모달 관련
  const [modalOpen, setModalOpen] = useState(false);
  const [modalImages, setModalImages] = useState([]);
  const [modalIndex, setModalIndex] = useState(0);

  // 2개만 랜덤으로 표시
  useEffect(() => {
    setVisiblePrompts(availablePrompts.slice(0, 2));
  }, [availablePrompts]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    function getRandomItems(arr, n) {
      const shuffled = [...arr].sort(() => 0.5 - Math.random());
      return shuffled.slice(0, n);
    }

    setVisiblePrompts(getRandomItems(availablePrompts, 2));
  }, [availablePrompts]);

  const sendMessage = async (text) => {
    const userMessage = { role: "user", text };
    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    try {
      const params = new URLSearchParams();
      params.append("user_id", "adminadmin"); // 테스트용 아이디
      params.append("query", text);

      console.log("📤 요청 보냄:", Object.fromEntries(params.entries()));

      // 일부러 2초 지연 (로딩 스피너용)
      // await new Promise((res) => setTimeout(res, 2000));

      const res = await axiosInstance.post("/search/image/", params);
      const data = res.data;

      let botText = "";
      let imageIds = [];

      if (data.type === "info_search") {
        botText = data.answer || "관련 정보를 찾을 수 없습니다.";
        // photo_ids 있을 경우 이미지도 추가
        if (Array.isArray(data.photo_ids) && data.photo_ids.length > 0) {
          imageIds = data.photo_ids.map((id) => `/images/${id}.jpg`);
        }
      } else if (data.type === "photo_search") {
        // photo_ids가 없거나 비어있으면 안내 메시지
        if (!Array.isArray(data.photo_ids) || data.photo_ids.length === 0) {
          botText = "찾으시는 사진이 없습니다. 다른 내용으로 검색해보시겠어요?";
        } else {
          botText = data.answer || "";
          imageIds = data.photo_ids.map((id) => `/images/grid-images/${id}.jpg`);
        }
      } else if (data.type === "conversation") {
        botText = data.answer || "관련 정보를 찾을 수 없습니다.";
        // photo_ids 있을 경우 이미지도 추가
        if (Array.isArray(data.photo_ids) && data.photo_ids.length > 0) {
          imageIds = data.photo_ids.map((id) => `/images/${id}.jpg`);
        }
      } else {
        botText = "알 수 없는 응답 형식입니다.";
      }

      const botMessage = {
        role: "bot",
        text: botText,
        images: imageIds,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (e) {
      const botMessage = {
        role: "bot",
        text: "응답을 불러오는 데 실패했습니다.",
        images: [],
      };
      setMessages((prev) => [...prev, botMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSend = () => {
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

  const handlePromptClick = (prompt) => {
    setInput(""); // reset input
    sendMessage(prompt);

    // 사용한 프롬프트 제거
    setAvailablePrompts((prev) => prev.filter((p) => p !== prompt));
  };

  const openImageModal = (images, index) => {
    setModalImages(images);
    setModalIndex(index);
    setModalOpen(true);
  };

  const closeImageModal = () => {
    setModalOpen(false);
    setModalImages([]);
    setModalIndex(0);
  };

  return (
    <>
      <div className="chat w-[448px] h-[448px] flex flex-col justify-between p-4 bg-white rounded-xl">
        {/* 메시지 출력 */}
        <div className="flex flex-col gap-3 mb-2 overflow-y-auto">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`max-w-[80%] w-fit text-sm px-4 py-2 rounded-xl ${
                msg.role === "user"
                  ? "self-end bg-black text-white rounded-tr-none mr-1"
                  : "self-start bg-white text-gray-800 border border-gray-200 rounded-tl-none shadow-sm"
              }`}
            >
              <p className="mb-1">{msg.text}</p>
              {msg.images && msg.images.length > 0 && (
                <div className="inline-flex flex-wrap gap-2 mt-2">
                  {msg.images.map((src, i) => (
                    <div
                      key={i}
                      className="overflow-hidden border rounded-lg aspect-square w-[88px] h-[88px]"
                      onClick={() => openImageModal(msg.images, i)}
                    >
                      <Image
                        src={src}
                        alt={`response image ${i + 1}`}
                        width={112}
                        height={112}
                        className="object-cover w-full h-full"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {isTyping && (
            <div className="self-start bg-white border border-gray-200 text-gray-400 rounded-xl px-4 py-2 text-sm w-fit max-w-[80%] shadow-sm rounded-tl-none">
              포키가 찾아보는 중<span className="typing" />
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div>
          {/* 프롬프트 예시 */}
          <div className="flex flex-col gap-1 mb-2">
            {visiblePrompts.map((text, idx) => (
              <button
                key={idx}
                onClick={() => handlePromptClick(text)}
                className="w-full px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                {text}
              </button>
            ))}
          </div>

          {/* 입력 영역 */}
          <div className="flex items-center h-12 gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
              placeholder="찾고 싶은 사진 또는 정보를 입력하세요"
              className="flex-1 h-full px-4 py-3 text-sm border rounded-lg"
            />
            <button
              onClick={handleSend}
              className="flex items-center justify-center w-12 h-full text-white rounded-lg group bg-cyan-400 hover:bg-[#86efac]"
            >
              <div className="w-3 h-3 bg-white rounded-full group-hover:hidden" />
              <span className="hidden text-sm font-semibold group-hover:inline">전송</span>
            </button>
          </div>
        </div>
      </div>
      {modalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={closeImageModal} // 외부 클릭 시 닫기
        >
          <div
            className="relative bg-white rounded-xl p-4 shadow-xl max-w-[90%] max-h-[90%] flex flex-col items-center z-40"
            onClick={(e) => e.stopPropagation()} // 모달 내용 클릭 시 닫히지 않도록
          >
            <button
              onClick={closeImageModal}
              className="absolute z-50 text-2xl font-bold text-gray-500 top-2 right-2 hover:text-black"
              aria-label="Close"
            >
              <X strokeWidth={0.8} />
            </button>
            <div className="relative flex items-center justify-center">
              {modalIndex > 0 && (
                <button
                  onClick={() => setModalIndex(modalIndex - 1)}
                  className="absolute left-[-80px] top-1/2 -translate-y-1/2 p-2 rounded-full bg-white shadow hover:bg-gray-100"
                  aria-label="Previous Image"
                >
                  <ChevronLeft
                    size={32}
                    strokeWidth={0.5}
                  />
                </button>
              )}
              <Image
                src={modalImages[modalIndex]}
                alt={`Selected ${modalIndex + 1}`}
                width={600}
                height={600}
                className="object-contain mt-6 max-w-full max-h-[80vh] rounded-md"
                priority
              />
              {modalIndex < modalImages.length - 1 && (
                <button
                  onClick={() => setModalIndex(modalIndex + 1)}
                  className="absolute right-[-80px] top-1/2 -translate-y-1/2 p-2 rounded-full bg-white shadow hover:bg-gray-100"
                  aria-label="Next Image"
                >
                  <ChevronRight
                    size={32}
                    strokeWidth={0.5}
                  />
                </button>
              )}
            </div>
            <div className="px-4 py-1 mt-4 text-sm text-gray-700 bg-gray-300 font-base rounded-3xl">
              {modalIndex + 1} / {modalImages.length}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
