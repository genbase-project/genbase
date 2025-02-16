import { useState } from 'react';
import { toast } from '@/hooks/use-toast';
import { ENGINE_BASE_URL, fetchWithAuth, setAuthCredentials, setEngineUrl } from '@/config';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface AuthPageProps {
  onAuthSuccess: () => void;
}

export const AuthPage = ({ onAuthSuccess }: AuthPageProps) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [engineUrl, setEngineUrlState] = useState(ENGINE_BASE_URL);

  const testAndSaveCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Test the credentials with a simple API call
      const headers = {
        'Authorization': `Basic ${btoa(`${username}:${password}`)}`
      };
      await fetchWithAuth(`${engineUrl}/module/project/default/list`, {
        skipAuth: true, // Skip the default auth handling
        headers: headers
      });

      // If the call succeeds, save the credentials
      setAuthCredentials(username, password);
      toast({
        title: "Success",
        description: "Authentication credentials saved"
      });
      onAuthSuccess();
    } catch (error) {
      toast({
        title: "Error",
        description: "Invalid credentials",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <img
            className="mx-auto h-20 w-auto"
            src="/logo.png"
            alt="Logo"
          />
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Genbase Studio
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Please enter your credentials to continue
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={testAndSaveCredentials}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="username" className="sr-only">
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div 
            className="flex items-center justify-between text-sm cursor-pointer py-2" 
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <span className="text-gray-600">Advanced Settings</span>
            {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>

          {showAdvanced && (
            <div className="rounded-md shadow-sm -space-y-px">
              <div>
                <label htmlFor="engine-url" className="sr-only">
                  Engine URL
                </label>
                <input
                  id="engine-url"
                  type="text"
                  className="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                  placeholder="Engine URL"
                  value={engineUrl}
                  onChange={(e) => {
                    setEngineUrlState(e.target.value);
                    setEngineUrl(e.target.value);
                  }}
                />
              </div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-neutral-700 hover:bg-neutral-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              {isLoading ? 'Authenticating...' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
