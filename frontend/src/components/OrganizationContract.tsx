import React, { useState, useEffect } from 'react';
import axiosInstance from '../axiosInstance';

const AdminContractStatus: React.FC = () => {
    const [organizations, setOrganizations] = useState<any[]>([]);
    const [selectedOrg, setSelectedOrg] = useState<string>('');
    const [newStatus, setNewStatus] = useState<string>('inactive');
    const [adminPassword, setAdminPassword] = useState<string>('');
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    useEffect(() => {
        const fetchOrganizations = async () => {
            setLoading(true); // Start loading when fetching organizations
            try {
                const response = await axiosInstance.get('/organization/all_organizations');
                const orgs = response.data.organizations || [];

                if (orgs.length > 0) {
                    setOrganizations(orgs);
                    setSelectedOrg(orgs[0].uuid); // Safely set first organization
                } else {
                    setError("No organizations found.");
                }
            } catch (err: any) {
                if (err.response?.status === 403) {
                    setError("Unauthorized request. Please check your token or credentials.");
                } else {
                    setError("Error fetching organizations. Please try again.");
                }
            } finally {
                setLoading(false); // Stop loading after fetching organizations
            }
        };

        fetchOrganizations();
    }, []);

    const handleStatusChange = async () => {
        // Validate input
        if (!selectedOrg) {
            setError('Please select an organization.');
            return;
        }
        if (!adminPassword) {
            setError('Admin password is required.');
            return;
        }

        setLoading(true); // Set loading state when making the request
        setError(null);
        setSuccessMessage(null);

        try {
            const response = await axiosInstance.post('/organization/change_contract_status', {
                org_uuid: selectedOrg,
                new_status: newStatus,
                admin_password: adminPassword,
            });

            setSuccessMessage(response.data.message);
        } catch (err: any) {
            if (err.response?.status === 403) {
                setError("Unauthorized action. Please verify your credentials.");
            } else if (err.response?.status === 400) {
                setError("Invalid request. Please check the data you're sending.");
            } else {
                setError(err.response?.data?.error || 'Error changing contract status.');
            }
        } finally {
            setLoading(false); // Stop loading after the request is finished
        }
    };

    return (
        <div>
            <h1>Change Organization Contract Status</h1>

            <div>
                <label htmlFor="orgSelect">Select Organization:</label>
                <select
                    id="orgSelect"
                    value={selectedOrg}
                    onChange={(e) => setSelectedOrg(e.target.value)}
                    disabled={loading || organizations.length === 0} // Disable select if loading or no orgs
                >
                    {organizations.length > 0 ? (
                        organizations.map(org => (
                            <option key={org.uuid} value={org.uuid}>
                                {org.name}
                            </option>
                        ))
                    ) : (
                        <option>No organizations available</option>
                    )}
                </select>
            </div>

            <div>
                <label htmlFor="status">Contract Status:</label>
                <select
                    id="status"
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    disabled={loading}
                >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                </select>
            </div>

            <div>
                <label htmlFor="adminPassword">Admin Password:</label>
                <input
                    id="adminPassword"
                    type="password"
                    value={adminPassword}
                    onChange={(e) => setAdminPassword(e.target.value)}
                    disabled={loading}
                />
            </div>

            <button onClick={handleStatusChange} disabled={loading}>
                {loading ? 'Changing Status...' : 'Change Status'}
            </button>

            {successMessage && <p style={{ color: 'green' }}>{successMessage}</p>}
            {error && <p style={{ color: 'red' }}>{error}</p>}
        </div>
    );
};

export default AdminContractStatus;
