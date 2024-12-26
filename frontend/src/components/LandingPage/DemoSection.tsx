import React from 'react';
import demoResponse from '../../assets/images/demo_response.png';
import demoCitation from '../../assets/images/demo_citation.png';
import demoPage from '../../assets/images/demo_page.png';
import styles from '../../styles/landingpage/DemoSection.module.css';

const DemoSection: React.FC = () => {
  const demoItems = [
    {
      title: "Quick and accurate responses",
      description: "We optimized our model for speed and accuracy for medical use cases",
      image: demoResponse,
    },
    {
      title: "Citations",
      description: "Each response comes with citations and links to the cited, highlighted documents",
      image: demoCitation,
    },
    {
      title: "Highlighted sources",
      description: "Quick access to highlighted source material from which the answers were generated",
      image: demoPage,
    },
  ];

  return (
    <div className={styles['demo-section']}>
      <div className={styles['demo-container']}>
        {/* Large first item */}
        <div className={styles['large-item-container']}>
          <div className={styles['demo-item-text']}>
            <h3>{demoItems[0].title}</h3>
            <p>{demoItems[0].description}</p>
          </div>
          <div className={styles['demo-item-image-large']}>
            <img src={demoItems[0].image} alt={demoItems[0].title} />
          </div>
        </div>

        {/* Regular items container */}
        <div className={styles['regular-items-container']}>
          {demoItems.slice(1).map((item, index) => (
            <div key={index} className={styles['demo-item']}>
              <div className={styles['demo-item-text']}>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </div>
              <div className={styles['demo-item-image']}>
                <img src={item.image} alt={item.title} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DemoSection;
