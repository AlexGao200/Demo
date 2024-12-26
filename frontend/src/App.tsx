import './App.css'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import HomePage from './pages/Home';
import LoginPage from './pages/Login';
import About from './pages/About';
import RegisterPage from './pages/Register';
import Chat from './pages/Chat';
import ChatHistory from './pages/ChatHistory';
import PDFViewer from './components/MiniPDFViewer';
import { UserProvider } from './context/UserContext';
import { ThemeProvider } from './context/ThemeContext';
import PrivateRoute from './components/PrivateRoute';
import ProtectedRoute from './components/ProtectedRoute';
import DocumentViewer from './pages/DocumentViewer';
import { VerifyEmailSuccess, VerifyEmailFailure, VerifyEmailExpired, OrgCreateSuccess } from './components/VerifyEmail';
import EmailVerification from './pages/EmailVerification';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import CreateOrganization from './pages/CreateOrganization';
import VerifyEmailSent from './pages/VerifyEmailSent';
import LandingPage from './pages/LandingPage';
import UploadDashboard from './pages/UploadDashboard';
import AdminReviewPage from './pages/AdminReview';
import ChangePermissions from './components/ChangePermissions';
import AdminMessageCount from './components/MessageCount';
import PreDashboard from './pages/OrganizationLogin';
import OrganizationDashboard from './pages/OrganizationDashboard';
import AddAdmin from './pages/OrganizationAdmin';
import SubscriptionManagement from './pages/SubscriptionManagement';
import Products from './pages/Subscription';
import AdminDashboard from './pages/AdminDashboard';
import ErrorBoundary from './components/ErrorBoundary';
import JoinOrganization from './pages/JoinOrganization';

import './styles/global.css';

function App() {
 return (
    <ErrorBoundary>
      <UserProvider>
        <ThemeProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/home" element={<HomePage />} />
              <Route path="/about" element={<About />} />
              <Route path="/chat/:id" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
              <Route path="/library" element={<PrivateRoute element={UploadDashboard} />} />
              <Route path="/chat_history" element={<ProtectedRoute><ChatHistory /></ProtectedRoute>} />
              <Route path="/verify-email/:token" element={<EmailVerification />} />
              <Route path="/verify-email-sent" element={<VerifyEmailSent />} />
              <Route path ="/subscription-management" element={<SubscriptionManagement/>} />
              <Route path ="/subscription" element={<Products/>} />
              <Route path="/upload/adminreview" element={<PrivateRoute element={AdminReviewPage} />} />
              <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
              <Route path="/document/:fileKey" element={<PDFViewer />} />
              <Route path="/view-pdf" element={<PDFViewer />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/messagecount" element={<AdminMessageCount />} />
              <Route path="/reset-password/:token" element={<ResetPassword />} />
              <Route path="/verify-email/success" element={<VerifyEmailSuccess />} />
              <Route path="/verify-email/failure" element={<VerifyEmailFailure />} />
              <Route path="/changepermissions" element={<PrivateRoute element={ChangePermissions} />} />
              <Route path="/verify-email/expired" element={<VerifyEmailExpired />} />
              <Route path="/document/backend/tmp/:filename/:pageNumber" element={<DocumentViewer />} />
              <Route path="/create-organization" element={<CreateOrganization />} />
              <Route path="/org-create-success" element={<OrgCreateSuccess />} />
              <Route path="/" element={<LandingPage />} />
              <Route path="/organization-login" element={<PreDashboard />} />
              <Route path="/organization-admin" element={<AddAdmin />} />
              <Route path="/admin-dashboard" element = {<AdminDashboard/>} />
              <Route path="/join-organization" element = {<JoinOrganization/>} />
              <Route path="/organization/:organizationId" element={<ProtectedRoute><OrganizationDashboard /></ProtectedRoute>} />
            </Routes>
          </Router>
        </ThemeProvider>
      </UserProvider>
    </ErrorBoundary>
 );
}

export default App;
