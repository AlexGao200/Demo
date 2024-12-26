import React from 'react';
import '../styles/LoadingAnimation.css'; // Make sure this CSS file exists in the frontend-vite project

const LoadingAnimation: React.FC = () => {
  return (
    <div className="loading-animation">
      <div className="dot"></div>
      <div className="dot"></div>
      <div className="dot"></div>
    </div>
  );
};

export default LoadingAnimation;
