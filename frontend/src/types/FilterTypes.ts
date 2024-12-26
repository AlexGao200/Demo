import { NavigationCallbacks } from '../components/filters_new/BaseFilter';

export interface Index {
  id: string;
  name: string;
  display_name: string;
  role_of_current_user: string;
  visibility_options_for_user: string[];
}

export interface FilterState {
  [key: string]: any;
}

export interface FilterProps {
  indices: Index[];
  filters: FilterState;
  visibility: { [key: string]: string};
  uploadResult?: any;
}

export interface FilterStep {
  name: string;
  title: string;
  component: React.ComponentType<FilterStepProps>;
}

export interface FilterStepProps extends NavigationCallbacks {
  filterData: FilterProps;
}
