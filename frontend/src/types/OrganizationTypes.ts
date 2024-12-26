export interface OrganizationMember {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
}

export interface Organization {
    id: string;
    name: string;
    index_name: string;
    role_of_current_user: string;
}

export interface OrganizationWithProperty extends Organization {
    [key: string]: unknown; // For any additional properties
}

// Utility type for route parameters
export type RouteParams<T> = {
  [K in keyof T]: string;
};

// Define OrganizationDashboardParams
export interface OrganizationDashboardParamsBase {
  organizationId: string;
}

export type OrganizationDashboardParams = RouteParams<OrganizationDashboardParamsBase>;
