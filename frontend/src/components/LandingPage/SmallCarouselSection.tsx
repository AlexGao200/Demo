import React, { useEffect, useState } from 'react';
import Carousel from './Carousel';
import styles from '../../styles/landingpage/SmallCarouselSection.module.css';

interface SmallCarouselSectionProps {
  carousels: SmallCarousel[];
  onItemClick: (item: CarouselItem) => void;
}

const SmallCarouselSection: React.FC<SmallCarouselSectionProps> = ({ carousels, onItemClick }) => {
  const [itemsPerSlide, setItemsPerSlide] = useState(3);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 1024) {
        setItemsPerSlide(1);
      } else {
        setItemsPerSlide(3);
      }
    };

    handleResize(); // Initial check
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className={styles.smallCarouselSection}>
      {carousels.map((carousel) => (
        <div key={carousel.id} className={styles.carouselWrapper}>
          <Carousel
            items={carousel.items}
            itemsPerSlide={itemsPerSlide}
            className={styles.smallCarousel}
            title={carousel.title}
            onItemClick={onItemClick}
          />
        </div>
      ))}
    </div>
  );
};

export default SmallCarouselSection;
