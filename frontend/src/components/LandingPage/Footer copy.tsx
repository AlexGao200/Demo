import React from 'react'
import '../../styles/Footer.css';

const Footer: React.FC = () => {
    return (
        <footer className="footer">
            <div className="footer-container">
                <div className="footer-column">
                    <h4>Acaceta</h4>
                    <ul>
                        <li><a href="#medical-reps">For Medical Device Representatives</a></li>
                        <li><a href="#doctors">For Doctors</a></li>
                        <li><a href="#research">For Research</a></li>
                    </ul>
                </div>
                <div className="footer-column">
                    <h4>Safety Overview</h4>
                    <ul>
                        <li><a href="#safety">Safety overview</a></li>
                    </ul>
                </div>
                <div className="footer-column">
                    <h4>Company</h4>
                    <ul>
                        <li><a href="#about-us">About Us</a></li>
                        <li><a href="#contact-us">Contact Us</a></li>
                    </ul>
                </div>
                <div className="footer-column">
                    <h4>Terms & Policy</h4>
                    <ul>
                        <li><a href="#terms-of-use">Terms of Use</a></li>
                        <li><a href="#privacy-policy">Privacy Policy</a></li>
                    </ul>
                </div>
            </div>
            <div className="footer-bottom">
                <p>© Acaceta 2024-2024</p>
            </div>
        </footer>
    );
};

export default Footer;
