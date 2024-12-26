import React from 'react';

const VerifyEmailSuccess: React.FC = () => (
    <div style={styles.container}>
        <div style={styles.box}>
            <h1>Email Verification</h1>
            <p>Verification successful! You can now <a href="/login">log in</a>.</p>
        </div>
    </div>
);

const VerifyEmailFailure: React.FC = () => (
    <div style={styles.container}>
        <div style={styles.box}>
            <h1>Email Verification</h1>
            <p>Verification failed. Please try again.</p>
        </div>
    </div>
);

const VerifyEmailExpired: React.FC = () => (
    <div style={styles.container}>
        <div style={styles.box}>
            <h1>Email Verification</h1>
            <p>Verification link expired. Please request a new verification email.</p>
        </div>
    </div>
);

const OrgCreateSuccess: React.FC = () => (
    <div style={styles.container}>
        <div style={styles.box}>
            <h1>Organization Created</h1>
            <p>Your organization has been created successfully!</p>
        </div>
    </div>
);

const styles: { [key: string]: React.CSSProperties } = {
    container: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        backgroundColor: '#f0f4f8',
    },
    box: {
        padding: '20px',
        borderRadius: '8px',
        backgroundColor: '#fff',
        boxShadow: '0 0 10px rgba(0,0,0,0.1)',
        textAlign: 'center',
    },
};

export { VerifyEmailSuccess, VerifyEmailFailure, VerifyEmailExpired, OrgCreateSuccess };
