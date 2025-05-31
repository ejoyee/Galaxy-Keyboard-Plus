'use client';

import { useState, useEffect } from 'react';

export default function QnaPage() {
  const [question, setQuestion] = useState('');
  const [submittedQuestions, setSubmittedQuestions] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ragResponse, setRagResponse] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [displayedText, setDisplayedText] = useState('');
  const [showResponse, setShowResponse] = useState(false);

  // 타이핑 애니메이션 효과
  useEffect(() => {
    if (ragResponse && isTyping) {
      let index = 0;
      setDisplayedText('');
      const timer = setInterval(() => {
        if (index < ragResponse.length) {
          setDisplayedText(prev => prev + ragResponse[index]);
          index++;
        } else {
          clearInterval(timer);
          setIsTyping(false);
        }
      }, 50); // 50ms마다 한 글자씩 타이핑

      return () => clearInterval(timer);
    }
  }, [ragResponse, isTyping]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setIsSubmitting(true);
    setShowResponse(false);
    setRagResponse('');
    setDisplayedText('');
    
    try {
      const response = await fetch('http://k12e201.p.ssafy.io:8090/rag/qa/query', {
        method: 'POST',
        headers: {
          'accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question.trim()
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        // 질문을 목록에 추가
        const newQuestion = {
          id: Date.now(),
          text: question.trim(),
          timestamp: new Date().toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit'
          }),
          response: data.rag_response
        };
        
        setSubmittedQuestions(prev => [newQuestion, ...prev]);
        
        // RAG 응답 표시 및 타이핑 애니메이션 시작
        setRagResponse(data.rag_response);
        setShowResponse(true);
        setIsTyping(true);
        
        setQuestion('');
      } else {
        console.error('API 요청 실패:', response.status);
        alert('질문 처리 중 오류가 발생했습니다.');
      }
    } catch (error) {
      console.error('API 요청 오류:', error);
      alert('네트워크 오류가 발생했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuestionChange = (e) => {
    setQuestion(e.target.value);
  };

  const closeResponse = () => {
    setShowResponse(false);
    setRagResponse('');
    setDisplayedText('');
    setIsTyping(false);
  };

  return (
    <div className="min-h-screen relative overflow-hidden font-pretendard">
      {/* Deep Space Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-black via-gray-900 to-black">
        <div className="absolute inset-0 bg-gradient-to-tl from-cyan-500/10 via-transparent to-blue-500/10"></div>
        <div className="absolute top-1/4 right-1/4 w-[600px] h-[600px] bg-gradient-to-br from-cyan-400/20 to-blue-600/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 left-1/4 w-[500px] h-[500px] bg-gradient-to-tr from-purple-400/15 to-pink-600/15 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-r from-indigo-900/10 via-purple-900/10 to-black rounded-full blur-3xl"></div>
      </div>

      {/* Stars and particles effect */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(50)].map((_, i) => (
          <div
            key={i}
            className="absolute bg-white rounded-full animate-pulse"
            style={{
              width: `${Math.random() * 2 + 1}px`,
              height: `${Math.random() * 2 + 1}px`,
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              opacity: Math.random() * 0.8 + 0.2,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${3 + Math.random() * 4}s`
            }}
          />
        ))}
      </div>

      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-6xl">
          {/* Header */}
          <div className="text-center mb-16">
            <div className="mb-8">
              <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-bold bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent mb-4 whitespace-nowrap">
                Galaxy Keyboard Plus
              </h1>
            </div>
            <h3 className="text-3xl md:text-4xl lg:text-5xl font-medium text-white/90 mb-8">
              Q&A Session
            </h3>
            <p className="text-gray-300 text-lg md:text-xl lg:text-2xl max-w-4xl mx-auto leading-relaxed font-medium">
              발표에 대한 질문이나 궁금한 점을 자유롭게 남겨주세요
            </p>
          </div>

          {/* Question Input Form */}
          <div className="mb-16">
            <form onSubmit={handleSubmit} className="space-y-8">
              <div className="relative group">
                <textarea
                  value={question}
                  onChange={handleQuestionChange}
                  placeholder="질문을 입력해주세요..."
                  rows={6}
                  className="w-full px-10 py-8 text-lg md:text-xl lg:text-2xl bg-white/5 backdrop-blur-xl border-2 border-white/20 rounded-3xl text-white placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-cyan-400/50 focus:border-cyan-400/50 transition-all duration-300 resize-none group-hover:bg-white/10 group-hover:border-white/30 font-medium"
                  disabled={isSubmitting}
                />
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
              </div>

              <div className="flex justify-center">
                <button
                  type="submit"
                  disabled={isSubmitting || !question.trim()}
                  className="relative px-16 py-6 text-lg md:text-xl lg:text-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white font-bold rounded-2xl transition-all duration-300 transform hover:scale-105 hover:shadow-2xl hover:shadow-cyan-500/40 focus:outline-none focus:ring-4 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-transparent overflow-hidden"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-white/20 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-300"></div>
                  <span className="relative flex items-center gap-3 font-bold">
                    {isSubmitting ? (
                      <>
                        <div className="animate-spin rounded-full h-7 w-7 border-b-3 border-white"></div>
                        AI가 답변 중...
                      </>
                    ) : (
                      '질문하기'
                    )}
                  </span>
                </button>
              </div>
            </form>
          </div>

          {/* Submitted Questions */}
          {submittedQuestions.length > 0 && (
            <div className="max-w-5xl mx-auto">
              <h3 className="text-2xl md:text-3xl lg:text-4xl font-bold text-white mb-10 text-center">
                질문 기록
              </h3>
              <div className="space-y-6 max-h-[500px] overflow-y-auto pr-4">
                {submittedQuestions.map((q, index) => (
                  <div
                    key={q.id}
                    className="group p-8 bg-white/5 backdrop-blur-xl border-2 border-white/10 rounded-2xl hover:bg-white/10 hover:border-white/20 transition-all duration-300 transform hover:scale-[1.02]"
                    style={{
                      animationDelay: `${index * 0.1}s`
                    }}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <span className="text-base md:text-lg text-cyan-400 font-bold">
                        질문 #{submittedQuestions.length - index}
                      </span>
                      <span className="text-sm text-gray-400 font-medium">
                        {q.timestamp}
                      </span>
                    </div>
                    <p className="text-white text-base md:text-lg lg:text-xl leading-relaxed font-medium mb-4">{q.text}</p>
                    {q.response && (
                      <div className="mt-4 p-4 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-xl border border-cyan-400/20">
                        <p className="text-cyan-300 text-sm font-bold mb-2">AI 답변:</p>
                        <p className="text-white text-sm md:text-base leading-relaxed">{q.response}</p>
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 to-blue-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Full Screen RAG Response Modal */}
        {showResponse && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-xl z-50 flex items-center justify-center p-4">
            <div className="w-full max-w-4xl">
              {/* Close Button */}
              <div className="flex justify-end mb-6">
                <button
                  onClick={closeResponse}
                  className="text-white/60 hover:text-white text-2xl transition-colors duration-200"
                >
                  ✕
                </button>
              </div>
              
              {/* Response Content */}
              <div className="text-center">
                <div className="mb-8">
                  <h2 className="text-2xl md:text-3xl lg:text-4xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent mb-4">
                    AI 답변
                  </h2>
                  <div className="w-20 h-1 bg-gradient-to-r from-cyan-500 to-blue-500 mx-auto rounded-full"></div>
                </div>
                
                <div className="bg-white/5 backdrop-blur-xl border-2 border-white/20 rounded-3xl p-8 md:p-12">
                  <p className="text-white text-xl md:text-2xl lg:text-3xl leading-relaxed font-medium text-left">
                    {displayedText}
                    {isTyping && (
                      <span className="inline-block w-0.5 h-6 md:h-8 bg-cyan-400 ml-1 animate-pulse"></span>
                    )}
                  </p>
                </div>
                
                {!isTyping && (
                  <div className="mt-8">
                    <button
                      onClick={closeResponse}
                      className="px-8 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold rounded-xl transition-all duration-300 transform hover:scale-105"
                    >
                      확인
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}