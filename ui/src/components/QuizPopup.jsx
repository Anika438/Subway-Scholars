import React, { useState } from 'react';
import './QuizPopup.css';

function QuizPopup({ questions, loading, topic, streak, onComplete }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selected, setSelected] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [allCorrect, setAllCorrect] = useState(true);

  if (loading || !questions || questions.length === 0) {
    return (
      <div className="quiz-overlay">
        <div className="quiz-popup">
          <div className="quiz-header">
            <span className="quiz-header-icon">🚫</span>
            <span className="quiz-header-text">DISTRACTION DETECTED!</span>
          </div>
          <div className="quiz-loading">
            <div className="quiz-spinner" />
            <p>Generating questions about <strong>{topic}</strong>...</p>
          </div>
        </div>
      </div>
    );
  }

  const question = questions[currentIndex];
  const isCorrect = selected === question?.correct_answer;

  const handleSelect = (option) => {
    if (showResult) return;
    setSelected(option);
    setShowResult(true);

    const correct = option === question.correct_answer;
    if (!correct) setAllCorrect(false);

    // Move to next or finish
    setTimeout(() => {
      if (currentIndex + 1 >= questions.length) {
        onComplete(allCorrect && correct);
      } else {
        setCurrentIndex(prev => prev + 1);
        setSelected(null);
        setShowResult(false);
      }
    }, 1400);
  };

  return (
    <div className="quiz-overlay">
      <div className={`quiz-popup ${showResult ? (isCorrect ? 'correct' : 'wrong') : ''}`}>
        {/* Header */}
        <div className="quiz-header">
          <span className="quiz-header-icon">🚫</span>
          <span className="quiz-header-text">FOCUS PENALTY!</span>
          {streak > 0 && <span className="quiz-streak-badge">🔥 {streak}</span>}
        </div>

        {/* Progress */}
        <div className="quiz-progress">
          Question {currentIndex + 1} of {questions.length} — <em>{topic}</em>
        </div>

        {/* Progress dots */}
        <div className="quiz-dots">
          {questions.map((_, i) => (
            <div
              key={i}
              className={`quiz-dot ${
                i < currentIndex ? 'dot-done' :
                i === currentIndex ? 'dot-active' : ''
              }`}
            />
          ))}
        </div>

        {/* Question */}
        <div className="quiz-question">
          {question?.question}
        </div>

        {/* Options */}
        <div className="quiz-options">
          {question?.options?.map((opt, i) => {
            let optClass = 'quiz-option';
            if (showResult) {
              if (opt === question.correct_answer) optClass += ' option-correct';
              else if (opt === selected) optClass += ' option-wrong';
              else optClass += ' option-disabled';
            }
            return (
              <button
                key={i}
                className={optClass}
                onClick={() => handleSelect(opt)}
                disabled={showResult}
              >
                <span className="option-letter">{String.fromCharCode(65 + i)}</span>
                <span className="option-text">{opt}</span>
              </button>
            );
          })}
        </div>

        {/* Result feedback */}
        {showResult && (
          <div className={`quiz-feedback ${isCorrect ? 'feedback-correct' : 'feedback-wrong'}`}>
            <div className="feedback-icon">{isCorrect ? '✅' : '❌'}</div>
            <div className="feedback-text">
              {isCorrect ? 'CORRECT!' : 'WRONG!'}
            </div>
            {!isCorrect && question?.explanation && (
              <div className="feedback-explanation">{question.explanation}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default QuizPopup;
