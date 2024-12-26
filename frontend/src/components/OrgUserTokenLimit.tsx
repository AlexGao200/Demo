import React, { useState, useContext, useEffect } from 'react';
import { ThemeContext } from '../context/ThemeContext';
import { OrganizationMember } from '../types';
import { ThemeContextType } from '../types';
import axiosInstance from '../axiosInstance';


interface SetUserTokenLimitProps {
    orgUuid: string;
    members: Array<{ id: string; email: string }> | undefined;
}


const SetUserTokenLimit: React.FC<SetUserTokenLimitProps> = ({ orgUuid, members }) => {
    const { theme } = useContext(ThemeContext) as ThemeContextType;
    const [tokenLimit, setTokenLimit] = useState<number | null>(1000); // null means no limit (unlimited)
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState<string>(''); // For searching members
    const [filteredMembers, setFilteredMembers] = useState<OrganizationMember[]>([]);
    const [selectedMember, setSelectedMember] = useState<OrganizationMember | null>(null);

    // Handle search and filter functionality
    useEffect(() => {
        if (members) {
            const filtered = members.filter(member =>
                member.email.toLowerCase().includes(searchTerm.toLowerCase())
            );
            setFilteredMembers(filtered);
        } else {
            setFilteredMembers([]);
        }
    }, [searchTerm, members]);

    const handleSetTokenLimit = async () => {
        if (!selectedMember) {
            setError('Please select a member.');
            return;
        }

        setLoading(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const response = await axiosInstance.post('/organization/set_user_token_limit', {
                org_uuid: orgUuid,
                user_id: selectedMember.id,
                token_limit: tokenLimit,
            });

            setSuccessMessage(response.data.message);
        } catch (err: any) {
            setError(err.response?.data?.error || 'Error setting token limit.');
        } finally {
            setLoading(false);
        }
    };

    const handleRemoveTokenLimit = async () => {
        if (!selectedMember) {
            setError('Please select a member.');
            return;
        }

        setLoading(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const response = await axiosInstance.post('/organization/remove_user_token_limit', {
                org_uuid: orgUuid,
                user_id: selectedMember.id,
            });

            setSuccessMessage(response.data.message);
            setTokenLimit(null); // Set the local state to null to reflect the unlimited status
        } catch (err: any) {
            setError(err.response?.data?.error || 'Error removing token limit.');
        } finally {
            setLoading(false);
        }
    };

    // Apply the same theme-based styles as the other components
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
            marginTop: '0px',
            margin: '0 auto', // This keeps the button centered
            display: 'block', // Ensure it behaves as a block element to center
        },
    };

    return (
        <div style={themeStyles.container}>
            <h2 style={themeStyles.header}>Set or Remove User Token Limit</h2>

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

            {/* Select Member Dropdown */}
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
                                {member.email}
                            </option>
                        ))}
                    </select>
                </div>
            ) : (
                <p>No members found matching your search.</p>
            )}

            {/* Token Limit Input */}
            <div style={themeStyles.inputGroup}>
                <label htmlFor="tokenLimit" style={themeStyles.label}>Token Limit:</label>
                <input
                    type="number"
                    id="tokenLimit"
                    value={tokenLimit !== null ? tokenLimit : ''}
                    onChange={(e) => setTokenLimit(Number(e.target.value))}
                    disabled={loading || !selectedMember} // Disable if no member selected or loading
                    placeholder="Enter token limit"
                    style={themeStyles.input}
                />
            </div>

            {/* Action Buttons */}
            <div>
                <button onClick={handleSetTokenLimit} disabled={loading || !selectedMember} style={themeStyles.button}>
                    {loading ? 'Setting Token Limit...' : 'Set Token Limit'}
                </button>

                <button onClick={handleRemoveTokenLimit} disabled={loading || !selectedMember} style={themeStyles.button}>
                    {loading ? 'Removing Token Limit...' : 'Remove Token Limit (Unlimited)'}
                </button>
            </div>
        </div>
    );
};

export default SetUserTokenLimit;
