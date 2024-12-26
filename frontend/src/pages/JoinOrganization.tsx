import React, { useState, useEffect } from 'react';
import axiosInstance from '../axiosInstance';

const JoinOrganization = () => {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [message, setMessage] = useState('');
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    // Fetch all organizations for selection
    axiosInstance.get('/organization/get-all')
      .then(response => {
        setOrganizations(response.data.organizations);
      })
      .catch(error => {
        console.error('Error fetching organizations:', error);
      });
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    axiosInstance.post('/organization/join-request', {
      organization_id: selectedOrg,
      message: message
    })
      .then(response => {
        setFeedback('Request sent successfully!');
      })
      .catch(error => {
        setFeedback('Failed to send request.');
        console.error(error);
      });
  };

  return (
    <div>
      <h2>Request to Join Organization</h2>
      <form onSubmit={handleSubmit}>
        <label>Select Organization</label>
        <select value={selectedOrg} onChange={(e) => setSelectedOrg(e.target.value)}>
          <option value="">-- Select --</option>
          {organizations.map((org) => (
            <option key={org.organization_id} value={org.organization_id}>
              {org.organization_name}
            </option>
          ))}
        </select>

        <label>Message (Optional)</label>
        <textarea value={message} onChange={(e) => setMessage(e.target.value)} />

        <button type="submit">Submit Request</button>
      </form>

      {feedback && <p>{feedback}</p>}
    </div>
  );
};

export default JoinOrganization;
