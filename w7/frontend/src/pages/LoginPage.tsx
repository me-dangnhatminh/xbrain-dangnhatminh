import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Loader2, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Already logged in → redirect
  if (user) {
    navigate('/knowledge-bases', { replace: true });
    return null;
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username.trim(), password);
      navigate('/knowledge-bases');
    } catch (err: any) {
      // Map common Cognito error codes to user-friendly messages
      const code = err?.code ?? '';
      if (code === 'NotAuthorizedException') {
        setError('Incorrect username or password.');
      } else if (code === 'UserNotFoundException') {
        setError('User not found. Please check your username.');
      } else if (code === 'UserNotConfirmedException') {
        setError('Account not confirmed. Please verify your email.');
      } else if (err?.message === 'NEW_PASSWORD_REQUIRED') {
        setError('Your account requires a password reset. Please contact your administrator.');
      } else {
        setError(err?.message ?? 'Sign in failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 relative overflow-hidden p-4">
      {/* Minimalist background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />
      <div className="absolute left-0 right-0 top-0 -z-10 m-auto h-[310px] w-[310px] rounded-full bg-blue-400 opacity-20 blur-[100px]" />

      <div className="w-full max-w-md relative z-10 animate-in fade-in slide-in-from-bottom-8 duration-700">
        <Card className="w-full shadow-2xl shadow-blue-900/5 border-slate-200/60 backdrop-blur-sm bg-white/95">
          <CardHeader className="space-y-2 pb-8 pt-8 text-center">
            <div className="flex justify-center mb-2">
              <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold text-2xl shadow-lg shadow-blue-500/30 ring-4 ring-white">
                D
              </div>
            </div>
            <CardTitle className="text-2xl font-semibold tracking-tight text-slate-900">
              DocHub AI
            </CardTitle>
            <CardDescription className="text-sm text-slate-500 font-medium">
              Sign in with your Cognito account
            </CardDescription>
          </CardHeader>

          <form onSubmit={handleLogin}>
            <CardContent className="space-y-5 px-8">
              {/* Username */}
              <div className="space-y-2.5">
                <label htmlFor="username" className="text-[13px] font-semibold text-slate-700 uppercase tracking-wide">
                  Username
                </label>
                <Input
                  id="username"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e: any) => setUsername(e.target.value)}
                  className="w-full h-11 bg-slate-50/50 border-slate-200 transition-colors focus:ring-2 focus:ring-blue-500/20 placeholder:text-slate-400"
                  autoComplete="username"
                  required
                  disabled={loading}
                />
              </div>

              {/* Password */}
              <div className="space-y-2.5">
                <label htmlFor="password" className="text-[13px] font-semibold text-slate-700 uppercase tracking-wide">
                  Password
                </label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e: any) => setPassword(e.target.value)}
                    className="w-full h-11 pr-10 bg-slate-50/50 border-slate-200 transition-colors focus:ring-2 focus:ring-blue-500/20 placeholder:text-slate-400"
                    autoComplete="current-password"
                    required
                    disabled={loading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Error message */}
              {error && (
                <div className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2.5 animate-in fade-in slide-in-from-top-1">
                  <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                  <p className="text-[13px] text-red-600 font-medium">{error}</p>
                </div>
              )}
            </CardContent>

            <CardFooter className="px-8 pb-8 pt-4 flex-col gap-3">
              <Button
                className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-medium text-[15px] shadow-md shadow-blue-500/20 transition-all duration-200 relative overflow-hidden"
                type="submit"
                disabled={loading || !username.trim() || !password}
              >
                <span className={`flex items-center justify-center transition-all duration-300 ${loading ? 'opacity-0 scale-95' : 'opacity-100 scale-100'}`}>
                  Sign In
                </span>
                {loading && (
                  <span className="absolute inset-0 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 animate-spin text-white" />
                  </span>
                )}
              </Button>
            </CardFooter>
          </form>
        </Card>

        <p className="text-center text-xs text-slate-400 mt-6 font-medium">
          Secured by AWS Cognito · Enterprise Knowledge Management
        </p>
      </div>
    </div>
  );
}
