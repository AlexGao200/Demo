import React, { useState, useEffect, useRef, lazy, Suspense  } from 'react';
import styles from '../styles/landingpage/LandingPage.module.css';
import Footer from '../components/LandingPage/Footer';
import LandingHeader from '../components/LandingPage/LandingHeader';
import ModalCarousel from '../components/LandingPage/ModalCarousel';
import HeroSection from '../components/LandingPage/HeroSection';
import DemoSection from '../components/LandingPage/DemoSection';
import SmallCarouselSection from '../components/LandingPage/SmallCarouselSection';

import heroImage from '../assets/images/carousel/31.png';
import demoPage from '../assets/images/demo_page.png';
import demoCitation from '../assets/images/demo_citation.png';
import demoResponse from '../assets/images/demo_response.png';
import extra from '../assets/images/carousel/extra.png';
import extra2 from '../assets/images/carousel/extra2.png';
import extra3 from '../assets/images/carousel/extra3.png';
import extra4 from '../assets/images/carousel/extra4.png';
import extra5 from '../assets/images/carousel/extra5.png';
import extra6 from '../assets/images/carousel/extra6.png';
import extra7 from '../assets/images/carousel/extra7.png';
import extra8 from '../assets/images/carousel/extra8.png';
import extra9 from '../assets/images/carousel/extra9.png';
import extra10 from '../assets/images/carousel/extra10.png';
import extra11 from '../assets/images/carousel/extra11.png';
import extra12 from '../assets/images/carousel/extra12.png';
import extra13 from '../assets/images/carousel/extra13.png';
import extra14 from '../assets/images/carousel/extra14.png';
import image15 from '../assets/images/carousel/15.png';
import image16 from '../assets/images/carousel/16.png';
import image13 from '../assets/images/carousel/13.png';
import image21 from '../assets/images/carousel/21.png';
import image22 from '../assets/images/carousel/22.png';
import image23 from '../assets/images/carousel/23.png';
import image31 from '../assets/images/carousel/31.png';
import image32 from '../assets/images/carousel/32.png';
import image33 from '../assets/images/carousel/33.png';
import image41 from '../assets/images/carousel/41.png';
import image42 from '../assets/images/carousel/42.png';
import image51 from '../assets/images/carousel/51.png';
import image52 from '../assets/images/carousel/52.png';

// modal images:
import Cimage11 from '../assets/images/carouselmodal/11.png'
import Cimage12 from '../assets/images/carouselmodal/12.png'
import Cimage21 from '../assets/images/carouselmodal/21.png'
import Cimage22 from '../assets/images/carouselmodal/22.png'
import Cimage23 from '../assets/images/carouselmodal/23.png'
import Cimage24 from '../assets/images/carouselmodal/24.png'
import Cimage31 from '../assets/images/carouselmodal/31.png'
import Cimage41 from '../assets/images/carouselmodal/41.png'
import Cimage42 from '../assets/images/carouselmodal/42.png'
import Cimage51 from '../assets/images/carouselmodal/51.png'
import Cimage52 from '../assets/images/carouselmodal/52.png'
import Cimage61 from '../assets/images/carouselmodal/61.png'
import Cimage62 from '../assets/images/carouselmodal/62.png'

const LandingPage: React.FC = () => {
  const [headerHidden, setHeaderHidden] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [selectedItem, setSelectedItem] = useState<CarouselItem | null>(null);
  const [isMobile, setIsMobile] = useState<boolean>(false);
  const heroRef = useRef<HTMLDivElement | null>(null);

  // Handle modal state
  const handleModalOpen = (item: CarouselItem) => {
    setSelectedItem(item);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setTimeout(() => {
      setSelectedItem(null);
    }, 300);
  };

  // Handle responsive breakpoints
  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    // Set initial value
    handleResize();

    // Add event listener
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const smallCarousels: SmallCarousel[] = [
    {
      id: 2,
      title: "Explore",
      itemsPerSlide: 6,
      items: [
        {
          text: "Proprietary databases",
          image: image32,
          sections: [
            {
              type: 'text',
              content: 'Acaceta is AI trained on the documents that you provide. Those documents remain yours. Choose which of your files are publicly accessible, and which remain internal to your organization.'
            },
            {
              type: 'image',
              content: Cimage11,
              caption: "File visibility selection",
              imageStyle: { maxWidth: '80%', maxHeight: '400px' }
            },
            {
              type: 'text',
              content: "Grant members of your organization privileges to upload documents to your internal database as well as to make documents public under your organization's name. Additionally, process external requests to make a public document attributable to your organization"
            },
            {
              type: 'image',
              content: Cimage12,
              caption: "File Upload details",
              imageStyle: { maxWidth: '70%', maxHeight: '100%' }
            }
          ]
        },
        {
          text: "Centralized library for members and customers",
          image: image22,
          sections: [
            {
              type: 'text',
              content: 'Our centralized library system provides a unified access point for all documentation in an intuitive format.'
            },
            {
              type: 'image',
              content: Cimage21,
              caption: "Library System",
              imageStyle: { maxWidth: '100%', maxHeight: '100%' }
            },
            {
              type: 'text',
              content: 'Sort document by categories.'
            },
            {
              type: 'image',
              content: Cimage22,
              caption: "Category sorting",
              imageStyle: { maxWidth: '100%', maxHeight: '100%' }
            },
            {
              type: 'text',
              content: 'Specify what categories your documents belong to during upload.'
            },
            {
              type: 'image',
              content: Cimage23,
              caption: "Category Selection",
              imageStyle: { maxWidth: '80%', maxHeight: '80%' }
            },
            {
              type: 'text',
              content: 'Fine-grained categorization.'
            },
            {
              type: 'image',
              content: Cimage24,
              caption: "Subfield Selection",
              imageStyle: { maxWidth: '80%', maxHeight: '80%' }
            }
          ]
        },
        {
          text: "Provide product documentation and AI access to customers",
          image: image41,
          sections: [
            {
              type: 'text',
              content: 'Easily invite users to join your organization in Acaceta.'
            },
            {
              type: 'image',
              content: Cimage31,
              caption: "Documentation Access",
              imageStyle: { maxWidth: '70%', maxHeight: '80%' }
            }
          ]
        },
        {
          text: "R&D benefits",
          image: image13,
          sections: [
            {
              type: 'text',
              content: 'Researchers can upload papers that they are reading and interface with them using our model. For instance, say that a research is looking into different approaches to power usage in medical devices, or the impact of certain regulatory documentation on a product that they are building:'
            },
            {
              type: 'image',
              content: Cimage41,
              caption: "Example Research Paper",
              imageStyle: { maxWidth: '100%', maxHeight: '100%' }
            },
            {
              type: 'text',
              content: 'They can upload the document to their own personal database (we are planning on adding documents specific to teams) then directly interface with those groups of documents, asking questions that span multiple documents. '
            },
            {
              type: 'image',
              content: Cimage42,
              caption: "Example Query",
              imageStyle: { maxWidth: '100%', maxHeight: '100%' }
            }
          ]
        },
        {
          text: "Personal databases for users",
          image: image42,
          sections: [
            {
              type: 'text',
              content: 'Acaceta provides a personal database for each user where they can upload documents visible only to themselves.'
            },
            {
              type: 'image',
              content: Cimage51,
              caption: "Personal Database Interface",
              imageStyle: { maxWidth: '100%', maxHeight: '100%' }
            },
            {
              type: 'text',
              content: "Users can upload personal documents—whether conference research papers, developmental papers, or simply textbooks which they want the model to have access to when returning answers to them. For example, say that a user want to be able to ask questions related to sterilization in respect to the devices that they seek to learn about. They could upload a textbook that they have in their posession, say:"
            },
            {
              type: 'image',
              content: Cimage52,
              caption: "Personal Database Interface",
              imageStyle: { maxWidth: '80%', maxHeight: '100%' }
            },
            {
              type: 'text',
              content: 'The user would then be able to incorporate the information from the given resource into the queries, asking questions involving both data sources.'
            },
          ]
        },
        {
          text: "Enhanced training",
          image: extra3,
          sections: [
            {
              type: 'text',
              content: "Acaceta's AI-powered platform can augment medical device company training by creating a dynamic, personalized, and compliant learning environment."
            },
            {
              type: 'image',
              content: Cimage61,
              caption: "Example Query",
              imageStyle: { maxWidth: '100%', maxHeight: '100%' }
            },
            {
              type: 'image',
              content: Cimage62,
              caption: "Training Analytics",
              imageStyle: { maxWidth: '95%', maxHeight: '90%' }
            }
          ]
        },
      ],
    },
    {
      id: 3,
      itemsPerSlide: 8,
      title: "Upcoming",
      items: [
        {
          text: "Internal database integration",
          image: extra4,
          sections: [
            {
              type: 'text',
              content: "Acaceta will automatically find your documents and index them so that you don’t have to. From document discovery to question-answering, Acaceta can solve information knowledge a medical professional faces. Simply connect your existing document database solution with our service, and ask questions to get instant citation-backed-answers."
            }
          ]
        },
        {
          text: "Voice-to-chat and Voice Response",
          image: extra6,
          sections: [
            {
              type: 'text',
              content: "We are consciously setting a foundation for ourselves built upon testing and reliability. It is paramount that both our users and ourselves have the utmost confidence and knowledge of Acaceta's capabilites. For this reason, we make a committment to consistently share the results of our tests with our users and potential users."
            }
          ]
        },
        {
          text: "Exploring Possibilities Across the Health Industry",
          image: extra5,
          sections: [
            {
              type: 'text',
              content: "We are consciously setting a foundation for ourselves built upon testing and reliability. It is paramount that both our users and ourselves have the utmost confidence and knowledge of Acaceta's capabilites. For this reason, we make a committment to consistently share the results of our tests with our users and potential users."
            }
          ]
        },
        {
          text: "Testing and reliability is our identity",
          image: extra11,
          sections: [
            {
              type: 'text',
              content: "We are consciously setting a foundation for ourselves built upon testing and reliability. It is paramount that both our users and ourselves have the utmost confidence and knowledge of Acaceta's capabilites. For this reason, we make a committment to consistently share the results of our tests with our users and potential users."
            }
          ]
        },
        {
          text: "Testing metholodogy",
          image: extra12,
          sections: [
            {
              type: 'text',
              content: 'We are aggregating a collection of thousands of peer-reviewed questions and answers from medical experts. A benchmark that we have set for ourselves is to answer at least 95% of the questions correctly, with our model informing the user that they are unsure of the answer for the remaining 5%.'
            }
          ]
        },
        {
          text: "Comparative Studies",
          image: extra7,
          sections: [
            {
              type: 'text',
              content: "We are in the process of arranging a study comparing Acaceta's performance to medical device representatives so that both ourselves and our users can be fully aware of how our model compares to their own experts."
            }
          ]
        },
        {
          text: "In the operating room",
          image: extra13,
          sections: [
            {
              type: 'text',
              content: 'We are in the process of receiving FDA approval for usage in the operating room.'
            }
          ]
        },
        {
          text: "Instant access for consumers learning a product",
          image: extra10,
          sections: [
            {
              type: 'text',
              content: "The next major feature is creating a streamlined method for consumers to interface with a single document's manual."
            }
          ]
        },
      ],
    },
  ];

  const handleItemClick = (item: CarouselItem) => {
    setSelectedItem(item);
    setIsModalOpen(true);
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        setHeaderHidden(!entry.isIntersecting);
      },
      {
        threshold: isMobile ? 0.2 : 0.5,
        rootMargin: isMobile ? '-50px' : '0px'
      }
    );

    if (heroRef.current) {
      observer.observe(heroRef.current);
    }

    return () => {
      if (heroRef.current) {
        observer.unobserve(heroRef.current);
      }
    };
  }, [isMobile]);

  return (
    <div className={`${styles['landing-container']} ${styles['responsive-container']}`}>
      <LandingHeader
        headerHidden={headerHidden}
        className={`
          ${styles['landing-header']}
          ${styles['responsive-header']}
          ${headerHidden ? styles['header-hidden'] : ''}
        `}
      />

      <div ref={heroRef} className={styles['hero-wrapper']}>
        <HeroSection className={styles['responsive-hero']} />
      </div>

      <DemoSection className={styles['responsive-demo']} />



      <SmallCarouselSection
        carousels={smallCarousels}
        onItemClick={handleModalOpen}
        className={styles['responsive-carousel-section']}
      />

      <Footer className={styles['responsive-footer']} />

      <ModalCarousel
        isOpen={isModalOpen}
        onClose={handleModalClose}
        className="small-carousel"
        modalContent={selectedItem?.sections}
        title={selectedItem?.text}
      />
    </div>
  );
};

export default LandingPage;
