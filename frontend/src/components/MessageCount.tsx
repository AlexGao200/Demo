import React, { useState, useEffect, useContext, useMemo } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { ThemeContext } from '../context/ThemeContext';
import axiosInstance from '../axiosInstance';
import '../styles/MessageCount.css';
import { ThemeContextType } from '../types';


// Register the necessary Chart.js components for a Bar chart
Chart.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface MessageCountProps {
  organizationName: string;
}

interface MessageDataItem {
  month?: number;
  year: number;
  day?: string;
  total_messages: number;
}

const MessageCount: React.FC<MessageCountProps> = ({ organizationName }) => {
  const { theme } = useContext(ThemeContext) as ThemeContextType;
  const [messageData, setMessageData] = useState<MessageDataItem[] | null>(null);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [view, setView] = useState<'month' | 'week' | 'year'>('week');
  const [numOfUnits, setNumOfUnits] = useState<number>(4); // Controls how many weeks, months, or years to show
  const [chartKey, setChartKey] = useState<number>(0); // To force re-render on resize

  // const capitalizeWords = (str: string) => str.replace(/\b\w/g, (char) => char.toUpperCase());

  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  const fetchMessageData = async () => {
    if (!organizationName) {
      console.error("Organization name is missing!");
      setError("Organization name is required.");
      return;
    }

    try {
      setLoading(true);
      const response = await axiosInstance.post('/organization/message_count_by_org', {
        organization_name: organizationName,
        view: view,
      });
      setMessageData(response.data);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.error || 'An error occurred while fetching message data.');
      setMessageData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessageData();
  }, [organizationName, view, numOfUnits]);

  // Handle chart resizing on window resize
  useEffect(() => {
    const handleResize = () => {
      setChartKey((prevKey) => prevKey + 1); // Force chart to re-render on resize
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const getLastNWeeks = (n: number) => {
    const weeks = [];
    const currentDate = new Date();
    const currentDay = currentDate.getDay();
    const lastMonday = new Date(currentDate.setDate(currentDate.getDate() - (currentDay === 0 ? 6 : currentDay - 1)));

    for (let i = 0; i < n; i++) {
      const startOfWeek = new Date(lastMonday);
      startOfWeek.setDate(lastMonday.getDate() - i * 7);
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      weeks.push({
        label: `${startOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`,
        data: messageData?.[i]?.total_messages || 0,
      });
    }
    return weeks.reverse();
  };

  const getLastNMonths = (n: number) => {
    const months = [];
    const currentDate = new Date();
    for (let i = 0; i < n; i++) {
      const month = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1);
      months.push({
        label: `${monthNames[month.getMonth()]} ${month.getFullYear()}`,
        data: messageData?.[i]?.total_messages || 0,
      });
    }
    return months.reverse();
  };

  const getLastNYears = (n: number) => {
    const years = [];
    const currentYear = new Date().getFullYear();
    for (let i = 0; i < n; i++) {
      years.push({
        label: `${currentYear - i}`,
        data: messageData?.[i]?.total_messages || 0,
      });
    }
    return years.reverse();
  };

  const chartData = useMemo(() => {
    if (!messageData) return null;

    let combinedData: { label: string; data: number }[] = [];

    if (view === 'week') {
      combinedData = getLastNWeeks(numOfUnits);
    } else if (view === 'month') {
      combinedData = getLastNMonths(numOfUnits);
    } else if (view === 'year') {
      combinedData = getLastNYears(numOfUnits);
    }

    // Set a semi-transparent background color so grid lines are visible
    const backgroundColor = theme === 'dark' ? 'rgba(242, 228, 201, 0.7)' : 'rgba(128, 128, 128, 0.3)';
    const borderColor = theme === 'dark' ? '#F2E4C9' : 'rgba(128, 128, 128, 1)';

    return {
      labels: combinedData.map(item => item.label),
      datasets: [
        {
          label: `Messages Sent (${view})`,
          data: combinedData.map(item => item.data),
          backgroundColor: backgroundColor,
          borderColor: borderColor,
          borderWidth: 1,
        },
      ],
    };
  }, [messageData, theme, view, numOfUnits]);

  const themeStyles = {
    backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5',
    color: theme === 'dark' ? '#F5F5F5' : '#333333',
  };

  // Update slider background function
  const updateSliderBackground = (slider: HTMLInputElement) => {
    const max = parseInt(slider.max);
    const val = parseInt(slider.value);
    const percentage = (val / max) * 100;

    slider.style.background = `linear-gradient(
      to right,
      #F2E4C9 0%,
      #F2E4C9 ${percentage}%,
      ${theme === 'dark' ? '#333333' : '#FFFFFF'} ${percentage}%,
      ${theme === 'dark' ? '#333333' : '#FFFFFF'} 100%
    )`;
  };

  useEffect(() => {
    const slider = document.querySelector('.custom-slider') as HTMLInputElement;
    if (slider) {
      updateSliderBackground(slider);
      slider.addEventListener('input', function () {
        updateSliderBackground(slider);
      });
    }
  }, [numOfUnits, theme]);

  return (
    <div style={{ padding: '22px', ...themeStyles }}>
      {/* Title container */}
      <div style={{ textAlign: 'center', marginBottom: '20px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: theme === 'dark' ? '#F5F5F5' : '#333333', marginBottom: '-55px' }}>
          Message Count
        </h2>
      </div>

      {/* Graph controls */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', marginBottom: '10px' }}>
        <div style={{ marginBottom: '10px', display: 'flex', alignItems: 'center' }}>
          <label htmlFor="viewSelect" style={{ marginRight: '10px' }}>Select View</label>
          <select
            id="viewSelect"
            value={view}
            onChange={(e) => setView(e.target.value as 'week' | 'month' | 'year')}
            style={{ padding: '8px', borderRadius: '4px', width: '150px' }}
          >
            <option value="week">By Week</option>
            <option value="month">By Month</option>
            <option value="year">By Year</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center' }}>
          <label htmlFor="rangeSlider" style={{ marginRight: '10px' }}>
            Number of {view === 'week' ? 'Weeks' : view === 'month' ? 'Months' : 'Years'}
          </label>
          <input
            type="range"
            id="rangeSlider"
            name="rangeSlider"
            min="1"
            max="12"
            value={numOfUnits}
            onChange={(e) => setNumOfUnits(parseInt(e.target.value))}
            className="custom-slider"
            style={{ height: '5px', borderRadius: '5px', outline: 'none' }} // Make the slider skinnier
          />
          <span style={{ marginLeft: '5px' }}>{numOfUnits}</span>
        </div>
      </div>

      {/* Graph positioned under the controls */}
      {/* Graph positioned under the controls */}
      <div style={{ width: '100%', minHeight: '400px' }}> {/* Set minHeight to 400px or whatever value you prefer */}
        {chartData && (
          <Bar
            key={chartKey} // Use chartKey to force re-render on resize
            data={chartData}
            options={{
              responsive: true,
              maintainAspectRatio: false, // Important for dynamic resizing
              plugins: {
                legend: {
                  display: true,
                  position: 'top',
                  labels: {
                    boxWidth: 20,
                    padding: 30, // Added padding around the legend
                  },
                },
              },
              scales: {
                x: {
                  title: {
                    display: true,
                    text: 'Dates',
                    font: {
                      size: 16,
                    },
                    padding: {
                      top: 20,
                    },
                  },
                  ticks: {
                    color: theme === 'dark' ? '#F5F5F5' : '#333333',

                  },
                  grid: {
                    color: theme === 'dark' ? '#555555' : '#E0E0E0',
                    drawOnChartArea: true, // Ensure grid lines are drawn
                  },
                },
                y: {
                  title: {
                    display: true,
                    text: 'Message Count',
                    font: {
                      size: 16,
                    },
                    padding: {
                      top: 20, // Adjusted padding to match x-axis
                    },
                  },
                  ticks: {
                    color: theme === 'dark' ? '#F5F5F5' : '#333333',
                    maxTicksLimit: 9,
                  },
                  grid: {
                    color: theme === 'dark' ? '#555555' : '#E0E0E0',
                    drawOnChartArea: true, // Ensure grid lines are drawn
                  },
                },
              },
              layout: {
                padding: {
                  top: 30, // Increased padding between the legend and the graph
                },
              },
            }}
          />
        )}
      </div>


      {error && <p style={{ color: 'red', textAlign: 'center', width: '100%' }}>{error}</p>}
      {loading && <p style={{ textAlign: 'center', width: '100%' }}>Loading message data...</p>}
    </div>
  );
};

export default MessageCount;
