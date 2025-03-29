import { toast } from '@/hooks/use-toast';

interface LogoutButtonProps {
  className?: string;
  onSuccess?: () => void;
}

export const handleLogout = () => {
    // Remove token from localStorage
    localStorage.removeItem('auth_token');
    
    toast({
      title: "Success",
      description: "Logged out successfully"
    });

    // redirect to /
    window.location.href = '/';
    

  };


export const LogoutButton = ({ className = '', onSuccess }: LogoutButtonProps) => {


  return (
    <button
      onClick={handleLogout}
      className={`px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-md ${className}`}
    >
      Sign out
    </button>
  );
};