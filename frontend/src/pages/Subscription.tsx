import React, { useEffect, useState, useContext } from 'react';
import { UserContext } from '../context/UserContext';
import axiosInstance from '../axiosInstance';
import AppHeader from '../components/AppHeader';
import '../styles/Products.css';

const Products: React.FC = () => {
  const { user } = useContext(UserContext);
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [stripe, setStripe] = useState<any>(null);

  const stripePublicKey = 'pk_test_51Q9VqARtAgEFTutZJUJ8aPli3sBs2OriJjU9U4d3sgzmmxgCjZfprbP7tXkmzK2G7s78RewLdpc9YVhI3Jg7IK0000LJG7lvaR';

  useEffect(() => {
    async function fetchProducts() {
      try {
        const response = await axiosInstance.get('/products');
        if (Array.isArray(response.data)) {
          setProducts(response.data);
        } else {
          setError('Unexpected response format');
        }
        setLoading(false);
      } catch (err) {
        console.error('Error fetching products:', err);
        setError('Failed to load products');
        setLoading(false);
      }
    }

    const loadStripeJs = () => {
      const script = document.createElement('script');
      script.src = 'https://js.stripe.com/v3/';
      script.async = true;
      script.onload = () => {
        setStripe((window as any).Stripe(stripePublicKey));
      };
      document.body.appendChild(script);
    };

    loadStripeJs();
    fetchProducts();
  }, []);

  const handleSubscribe = async (priceId: string) => {
    setIsRedirecting(true);
    try {
      const response = await axiosInstance.post('/create-checkout-session', { price_id: priceId });

      if (response?.data?.id) {
        const sessionId = response.data.id;

        if (!stripe) {
          throw new Error("Stripe.js has not been loaded.");
        }

        const result = await stripe.redirectToCheckout({ sessionId });
        if (result.error) {
          setError('Failed to redirect to Stripe Checkout');
        }
      } else {
        setError('Unexpected response format');
      }
    } catch (error) {
      setError('Failed to create checkout session');
    } finally {
      setIsRedirecting(false);
    }
  };

  const renderContent = () => {
    if (loading) return <div className="products-loading">Loading products...</div>;
    if (error) return <div className="products-error">{error}</div>;

    return (
      <div className="products-content">
        <h1 className="products-title">Our Offerings</h1>
        {isRedirecting && <p className="redirect-message">Redirecting to Stripe...</p>}
        <div className="products-grid">
          {Array.isArray(products) && products.map((product) => (
            <div key={product.price_id} className="product-card">
              <h2 className="product-name">{product.product_name}</h2>
              <div className="product-details">
                <p className="product-price">
                  ${product.unit_amount} <span className="currency">{product.currency}</span>
                </p>
                <p className="product-billing">
                  {product.recurring === 'one-time' ? 'One-time payment' : `Billed ${product.recurring}`}
                </p>
              </div>
              <button
                onClick={() => handleSubscribe(product.price_id)}
                disabled={isRedirecting}
                className="subscribe-button"
              >
                {isRedirecting ? 'Processing...' : 'Select Plan'}
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="page-container">
      <AppHeader />
      <div className="page-content">
        {renderContent()}
      </div>
    </div>
  );
};

export default Products;
