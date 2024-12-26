import React, { useRef, useEffect, useState } from 'react';
import styles from '../../styles/landingpage/Carousel.module.css';

interface CarouselItem {
  text: string;
  image: string;
  modalContent: string;
}

interface CarouselProps {
  items: CarouselItem[];
  itemsPerSlide: number;
  className: string;
  title?: string;
  onItemClick: (item: CarouselItem) => void;
}

const Carousel: React.FC<CarouselProps> = ({ items, itemsPerSlide, className, title, onItemClick }) => {
  const carouselRef = useRef<HTMLDivElement>(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  const getItemWidth = (): number => {
    if (window.innerWidth <= 480) return 200;
    if (window.innerWidth <= 768) return 250;
    if (window.innerWidth <= 1024) return 300;
    return 380;
  };

  const next = () => {
    if (carouselRef.current) {
      const itemWidth = getItemWidth() + 20;
      const nextIndex = currentIndex + 1;
      carouselRef.current.scrollTo({
        left: nextIndex * itemWidth,
        behavior: 'smooth'
      });
      setCurrentIndex(nextIndex);
    }
  };

  const prev = () => {
    if (carouselRef.current) {
      const itemWidth = getItemWidth() + 20;
      const prevIndex = currentIndex - 1;
      carouselRef.current.scrollTo({
        left: prevIndex * itemWidth,
        behavior: 'smooth'
      });
      setCurrentIndex(prevIndex);
    }
  };

  const canScrollPrev = currentIndex > 0;
  const canScrollNext = currentIndex < items.length - 1;

  return (
    <div className={styles.smallCarousel}>
      {title && <h2 className={styles.smallCarouselTitle}>{title}</h2>}
      <div
        className={styles.smallCarouselInner}
        ref={carouselRef}
        onScroll={() => {
          if (carouselRef.current) {
            const itemWidth = getItemWidth() + 20;
            const newIndex = Math.round(carouselRef.current.scrollLeft / itemWidth);
            setCurrentIndex(newIndex);
          }
        }}
      >
        {items.map((item, index) => (
          <div
            key={index}
            className={styles.smallCarouselItem}
            onClick={() => onItemClick(item)}
            style={{ cursor: 'pointer' }}
          >
            <img src={item.image} alt={item.text} className={styles.smallCarouselImage} />
            <div className={styles.smallCarouselText}>{item.text}</div>
          </div>
        ))}
      </div>

      {/* Always show both buttons */}
      <button
        className={styles.carouselControlPrev}
        onClick={prev}
        aria-label="Previous slide"
      >
        ←
      </button>
      <button
        className={styles.carouselControlNext}
        onClick={next}
        aria-label="Next slide"
      >
        →
      </button>
    </div>
  );
};

export default Carousel;
