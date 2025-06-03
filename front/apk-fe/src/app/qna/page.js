'use client';

import { useState, useEffect } from 'react';

export default function QnaPage() {
  const [question, setQuestion] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ragResponse, setRagResponse] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [displayedText, setDisplayedText] = useState('');
  const [showResponse, setShowResponse] = useState(false);

  // 타이핑 애니메이션 효과 (한글 호환)
  useEffect(() => {
    if (ragResponse && isTyping) {
      // 응답 텍스트를 기본 문자열로 처리
      const responseText = String(ragResponse);
      let index = 0;
      setDisplayedText('');
      
      const timer = setInterval(() => {
        if (index < responseText.length) {
          setDisplayedText(responseText.substring(0, index + 1));
          index++;
        } else {
          clearInterval(timer);
          setIsTyping(false);
        }
      }, 60); // 60ms로 속도 조정

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
      const response = await fetch('https://k12e201.p.ssafy.io/search/qa/query', {
  method: 'POST',
  headers: {
    'accept': 'application/json',
    'Content-Type': 'application/json',
    'X-Bypass-Auth': 'adminadmin'
  },
  body: JSON.stringify({
    question: question.trim()
  })
});


      if (response.ok) {
        const data = await response.json();
        
        // 디버깅을 위한 로그
        console.log('API 응답 데이터:', data);
        console.log('rag_response:', data.rag_response);
        
        // RAG 응답 데이터 정리 (undefined 제거)
        let cleanResponse = data.rag_response;
        
        // null, undefined, 빈 문자열 처리
        if (!cleanResponse || cleanResponse === null || cleanResponse === undefined || cleanResponse === 'undefined') {
          cleanResponse = '응답을 받을 수 없습니다.';
        } else {
          // 문자열로 변환 후 청리
          cleanResponse = String(cleanResponse);
          
          // undefined 및 null 관련 제거 (더 강력하게)
          cleanResponse = cleanResponse
            .replace(/undefined/gi, '')
            .replace(/null/gi, '')
            .replace(/NaN/gi, '')
            .replace(/\s+undefined\s*/gi, '')
            .replace(/undefined\s*/gi, '')
            .replace(/\s*undefined/gi, '')
            .trim();
          
          // 정리 후 빈 문자열인 경우
          if (cleanResponse.length === 0) {
            cleanResponse = '해당 질문에 대한 정보를 찾을 수 없습니다.';
          }
        }
        
        console.log('정리된 응답:', cleanResponse);
        

        
        // RAG 응답 표시 및 타이핑 애니메이션 시작
        setRagResponse(cleanResponse);
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
        <div className="absolute top-1/4 right-1/4 w-[300px] sm:w-[400px] md:w-[600px] h-[300px] sm:h-[400px] md:h-[600px] bg-gradient-to-br from-cyan-400/20 to-blue-600/20 rounded-full blur-3xl"></div>
        <div className="absolute bottom-1/4 left-1/4 w-[250px] sm:w-[350px] md:w-[500px] h-[250px] sm:h-[350px] md:h-[500px] bg-gradient-to-tr from-purple-400/15 to-pink-600/15 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[400px] sm:w-[600px] md:w-[800px] h-[400px] sm:h-[600px] md:h-[800px] bg-gradient-to-r from-indigo-900/10 via-purple-900/10 to-black rounded-full blur-3xl"></div>
      </div>

      {/* Stars and particles effect */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(30)].map((_, i) => (
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

      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Main Content - centered vertically with top padding and bottom space for fixed footer */}
        <div className="flex-1 flex flex-col items-center justify-center p-4 pt-16 pb-20">
          <div className="w-full max-w-4xl xl:max-w-5xl">
            {/* Header - 상단 여백 추가 */}
            <div className="text-center mb-6 sm:mb-8 mt-8 sm:mt-12 md:mt-16">
              <div className="mb-3 sm:mb-4">
                <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl 2xl:text-8xl font-bold bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent mb-2 sm:mb-3 leading-relaxed py-2">
                  Galaxy Keyboard Plus
                </h1>
              </div>
              <h3 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-medium text-white/90 mb-3 sm:mb-4">
                Q&A Session
              </h3>
              <p className="text-gray-300 text-lg sm:text-xl md:text-2xl lg:text-3xl max-w-3xl mx-auto leading-relaxed font-medium px-4">
                발표에 대한 질문이나 궁금한 점을 자유롭게 남겨주세요
              </p>
            </div>

            {/* Question Input Form - 더 컴팩트하게 조정 */}
            <div className="mb-6 sm:mb-8">
              <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
                <div className="relative group">
                  <textarea
                    value={question}
                    onChange={handleQuestionChange}
                    placeholder="질문을 입력해주세요..."
                    rows={4}
                    className="w-full px-4 sm:px-6 md:px-8 py-4 sm:py-6 text-xl sm:text-2xl md:text-3xl lg:text-4xl placeholder:text-xl sm:placeholder:text-2xl md:placeholder:text-3xl lg:placeholder:text-4xl bg-white/5 backdrop-blur-xl border-2 border-white/20 rounded-2xl sm:rounded-3xl text-white placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-cyan-400/50 focus:border-cyan-400/50 transition-all duration-300 resize-none group-hover:bg-white/10 group-hover:border-white/30 font-medium"
                    disabled={isSubmitting}
                  />
                  <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-2xl sm:rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                </div>

                <div className="flex justify-center">
                  <button
                    type="submit"
                    disabled={isSubmitting || !question.trim()}
                    className="relative px-8 sm:px-12 md:px-16 py-3 sm:py-4 md:py-5 text-lg sm:text-xl md:text-2xl lg:text-3xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white font-bold rounded-xl sm:rounded-2xl transition-all duration-300 transform hover:scale-105 hover:shadow-2xl hover:shadow-cyan-500/40 focus:outline-none focus:ring-4 focus:ring-cyan-400 focus:ring-offset-2 focus:ring-offset-transparent overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-white/20 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-300"></div>
                    <span className="relative flex items-center justify-center gap-2 sm:gap-3 font-bold whitespace-nowrap">
                      {isSubmitting ? (
                        <>
                          <div className="animate-spin rounded-full h-5 sm:h-6 md:h-7 lg:h-8 w-5 sm:w-6 md:w-7 lg:w-8 border-b-2 sm:border-b-3 border-white"></div>
                          <span className="hidden sm:inline text-lg sm:text-xl md:text-2xl">관련 정보를 찾고 있어요...</span>
                          <span className="sm:hidden text-lg">처리중...</span>
                        </>
                      ) : (
                        <span className="text-lg sm:text-xl md:text-2xl lg:text-3xl">질문하기</span>
                      )}
                    </span>
                  </button>
                </div>
              </form>
            </div>


          </div>
        </div>

        {/* Professional Fixed Footer - Always Visible */}
        <footer className="fixed bottom-0 left-0 right-0 z-30 bg-black/80 backdrop-blur-md border-t border-white/10">
          <div className="max-w-7xl mx-auto px-4 py-3">
            <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 text-sm sm:text-base text-gray-400">
              <span className="font-medium text-white text-base sm:text-lg">Galaxy Keyboard Plus</span>
              <span>•</span>
              <span className="text-sm sm:text-base">SSAFY 12기 E201</span>
              <span>•</span>
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-sm sm:text-base">RAG 시스템</span>
              </div>
              <span>•</span>
              <span className="text-sm sm:text-base">🔍 벡터 검색 기반 응답</span>
              <span className="hidden sm:inline">•</span>
              <span className="text-gray-500 text-sm sm:text-base">© 2025 SSAFY</span>
            </div>
          </div>
        </footer>

        {/* Full Screen RAG Response Modal */}
        {showResponse && (
          <div className="fixed inset-0 bg-gradient-to-br from-slate-800/90 via-gray-700/90 to-slate-900/90 backdrop-blur-2xl z-50 flex items-center justify-center p-4">
            {/* Floating particles for visual enhancement */}
            <div className="absolute inset-0 overflow-hidden">
              {[...Array(15)].map((_, i) => (
                <div
                  key={i}
                  className="absolute bg-cyan-400/20 rounded-full animate-pulse"
                  style={{
                    width: `${Math.random() * 4 + 2}px`,
                    height: `${Math.random() * 4 + 2}px`,
                    left: `${Math.random() * 100}%`,
                    top: `${Math.random() * 100}%`,
                    opacity: Math.random() * 0.5 + 0.2,
                    animationDelay: `${Math.random() * 3}s`,
                    animationDuration: `${2 + Math.random() * 3}s`
                  }}
                />
              ))}
            </div>
            <div className="w-full max-w-3xl xl:max-w-4xl max-h-[90vh] overflow-y-auto">
              {/* Close Button */}
              <div className="flex justify-end mb-4 sm:mb-6 sticky top-0 z-10">
                <button
                  onClick={closeResponse}
                  className="text-white/60 hover:text-white text-xl sm:text-2xl transition-colors duration-200 bg-black/50 rounded-full w-8 h-8 sm:w-10 sm:h-10 flex items-center justify-center"
                >
                  ✕
                </button>
              </div>
              
              {/* Response Content */}
              <div className="text-center">
                <div className="mb-6 sm:mb-8">
                  <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent mb-3 sm:mb-4">
                    RAG 기반 답변
                  </h2>
                  <div className="w-16 sm:w-20 h-1 bg-gradient-to-r from-cyan-500 to-blue-500 mx-auto rounded-full"></div>
                </div>
                
                <div className="bg-gradient-to-br from-white/15 via-slate-100/10 to-white/15 backdrop-blur-2xl border-2 border-cyan-400/40 rounded-2xl sm:rounded-3xl p-6 sm:p-8 md:p-12 shadow-2xl shadow-cyan-400/20 relative overflow-hidden">
                  {/* Inner glow effect */}
                  <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 via-transparent to-blue-500/5 rounded-2xl sm:rounded-3xl"></div>
                  <div className="relative z-10">
                  <div className="text-white text-lg sm:text-xl md:text-2xl lg:text-3xl xl:text-4xl leading-relaxed font-medium text-left whitespace-pre-line break-words">
                    {displayedText.split('. ').map((sentence, index) => (
                      <span key={index}>
                        {sentence.trim()}
                        {index < displayedText.split('. ').length - 1 && (
                          <>
                            .<br /><br />
                          </>
                        )}
                      </span>
                    ))}
                    {isTyping && (
                      <span className="inline-block w-0.5 h-5 sm:h-6 md:h-7 lg:h-8 xl:h-9 bg-cyan-400 ml-1 animate-pulse"></span>
                    )}
                  </div>
                  </div>
                </div>
                
                {!isTyping && (
                  <div className="mt-6 sm:mt-8">
                    <button
                      onClick={closeResponse}
                      className="px-6 sm:px-8 py-2 sm:py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold rounded-lg sm:rounded-xl transition-all duration-300 transform hover:scale-105 text-lg sm:text-xl md:text-2xl"
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