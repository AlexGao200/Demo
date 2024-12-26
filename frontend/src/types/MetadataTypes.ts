export interface Subfield {
    id: string;
    name: string;
}

export interface SubfieldWithAreas extends Subfield {
    areas: string[];
}

export interface SubfieldPopupProps {
    organizationId: string;
    databaseTypes: string[];
    onSelectSubfields: (selectedSubfields: Subfield[]) => void;
}

export interface AreaPopupProps {
    isOpen: boolean;
    subfields: SubfieldWithAreas[];
    onAreasSelected: (selectedAreas: string[]) => void;
    onClose: () => void;
    showCreateArea: boolean;
}

export interface CreateAreaProps {
    subfields: SubfieldWithAreas[];
    onCreateSuccess: () => void;
    onClose: () => void;
}

export interface CreateOrganizationProps {
    onCreateSuccess: () => void;
    databaseType: string;
}

export interface OrganizationPopupProps {
    onSelectOrganizations: (orgNames: string[]) => void;
    databaseTypes: string[];
    onClose: () => void;
}

export interface CreateSubfieldProps {
    organizationId: string;
    databaseType: string;
    onClose: () => void;
    onSubfieldCreated?: () => void;
}

export interface PersonalPopupProps {
    onClose: () => void;
    onCreateNewOrganization: () => void;
    onSelectOrganization: (orgId: string) => void;
}

export interface PublicPopupProps {
    onClose: () => void;
    onCreateNewOrganization: () => void;
    onSelectOrganization: (orgId: string) => void;
}

export interface PublicUploadProps {
    onClose: () => void;
}

export interface UnifiedComponentProps {
    databaseTypes: string[];
    organizationId: string;
    onClose: () => void;
    onSelectOrganization: (orgNames: string[]) => void;
    onFilterComplete: (filters: { organization: string[], subfield: string[], area: string[], indices: string[] }) => void;
}

export interface OrganizationalComponentProps {
    databaseType: string;
}
