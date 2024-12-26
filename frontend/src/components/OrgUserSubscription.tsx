import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import axiosInstance from '../axiosInstance';
import { ThemeContext } from '../context/ThemeContext';
import { UserContext } from '../context/UserContext';
import { OrganizationMember } from '../types';
import { ThemeContextType, UserContextType } from '../types';


interface ManageUserSubscriptionProps {
    orgUuid: string;
    members: any[]; // Now passed from the parent component
}

const ManageUserSubscription: React.FC<ManageUserSubscriptionProps> = ({ orgUuid, members }) => {
    const { theme } = useContext(ThemeContext) as ThemeContextType;
    const { user, token } = useContext(UserContext) as UserContextType;
    const [newStatus, setNewStatus] = useState<string>('inactive');
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState<string>('');
    const [filteredMembers, setFilteredMembers] = useState<OrganizationMember[]>([]);
    const [selectedMember, setSelectedMember] = useState<OrganizationMember | null>(null);

    // Logging the members received from the parent
    useEffect(() => {
        console.log("Members passed from parent:", members);
    }, [members]);

    // Filter members based on the search term
    useEffect(() => {
        console.log("Current search term:", searchTerm);
        console.log("Members list for filtering:", members);

        const filtered = members.filter(member =>
            `${member.email || ''}`.toLowerCase().includes(searchTerm.toLowerCase())
        );

        console.log("Filtered members:", filtered);

        setFilteredMembers(filtered);
    }, [searchTerm, members]);

    const handleStatusChange = async () => {
        if (!selectedMember) {
            setError('Please select a member.');
            return;
        }

        setLoading(true);
        setError(null);
        setSuccessMessage(null);

        console.log("Attempting to change subscription status for member:", selectedMember);
        console.log("New status:", newStatus);
        console.log("Organization UUID being passed:", orgUuid);

        try {
            const response = await axiosInstance.post('/manage_user_subscription', {
                org_uuid: orgUuid,
                user_id: selectedMember.id,
                subscription_status: newStatus,
            }, {
                headers: {
                    Authorization: `Bearer ${token}`, // Include the token
                },
            });

            console.log("Subscription status change response:", response.data);
            setSuccessMessage(response.data.message);
        } catch (err: any) {
            console.error("Error changing subscription status:", err.response?.data?.error || err);
            setError(err.response?.data?.error || 'Error changing subscription status.');
        } finally {
            setLoading(false);
        }
    };

    const themeStyles = {
        container: {
            padding: '20px',
            maxWidth: '600px',
            margin: '0 auto',
            backgroundColor: theme === 'dark' ? '#1A1A1A' : '#F5F5F5',
            color: theme === 'dark' ? '#F5F5F5' : '#333',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        },
        header: {
            fontSize: '22px',
            marginBottom: '20px',
        },
        message: {
            color: 'green',
            marginBottom: '15px',
        },
        error: {
            color: 'red',
            marginBottom: '15px',
        },
        form: {
            display: 'flex',
            flexDirection: 'column' as const,
        },
        inputGroup: {
            marginBottom: '15px',
            display: 'flex',
            flexDirection: 'column' as const,
            alignItems: 'flex-start',
        },
        label: {
            marginBottom: '5px',
            fontWeight: 'bold',
        },
        input: {
            padding: '10px',
            fontSize: '16px',
            borderRadius: '4px',
            border: theme === 'dark' ? '1px solid #555' : '1px solid #ccc',
            width: '95%',
            backgroundColor: theme === 'dark' ? '#333' : '#fff',
            color: theme === 'dark' ? '#F5F5F5' : '#333',
        },
        select: {
            padding: '10px',
            fontSize: '16px',
            borderRadius: '4px',
            border: theme === 'dark' ? '1px solid #555' : '1px solid #ccc',
            width: '95%',
            backgroundColor: theme === 'dark' ? '#333' : '#fff',
            color: theme === 'dark' ? '#F5F5F5' : '#333',
        },
        button: {
            padding: '10px',
            backgroundColor: 'transparent',
            color: theme === 'dark' ? '#BB0000' : '#212121',
            border: theme === 'dark' ? '1px solid #BB0000' : '1px solid #212121',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '16px',
            width: '50%', // Adjust the width to 50% for a smaller button
            marginTop: '25px',
            margin: '0 auto', // This keeps the button centered
            display: 'block', // Ensure it behaves as a block element to center
        },
    };

    return (
        <div style={themeStyles.container}>
            <h2 style={themeStyles.header}>Manage User Subscription</h2>

            {successMessage && <p style={themeStyles.message}>{successMessage}</p>}
            {error && <p style={themeStyles.error}>{error}</p>}

            {/* Search Box */}
            <div style={themeStyles.inputGroup}>
                <label style={themeStyles.label}>Search for Member:</label>
                <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Enter email"
                    style={themeStyles.input}
                />
            </div>

            {/* Display filtered members or a message if none found */}
            {filteredMembers.length > 0 ? (
                <div style={themeStyles.inputGroup}>
                    <label style={themeStyles.label}>Select Member:</label>
                    <select
                        value={selectedMember?.id || ''}
                        onChange={(e) =>
                            setSelectedMember(filteredMembers.find(member => member.id === e.target.value) || null)
                        }
                        style={themeStyles.select}
                    >
                        <option value="" disabled>Select a member</option>
                        {filteredMembers.map(member => (
                            <option key={member.id} value={member.id}>
                                {member.email || '[No email]'}
                            </option>
                        ))}
                    </select>
                </div>
            ) : (
                <p>No members found matching your search.</p>
            )}

            <div style={themeStyles.inputGroup}>
                <label style={themeStyles.label}>Subscription Status:</label>
                <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    disabled={loading || !selectedMember}
                    style={themeStyles.select}
                >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                </select>
            </div>

            <button onClick={handleStatusChange} disabled={loading || !selectedMember} style={themeStyles.button}>
                {loading ? 'Changing Status...' : 'Change Status'}
            </button>
        </div>
    );
};

export default ManageUserSubscription;
