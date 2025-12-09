import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  Lock,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  ArrowLeft,
  Sparkles,
} from "lucide-react";

// Components
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type AuthMode = "login" | "signup";

interface AuthProps {
  onLogin: (userData: {
    username: string;
    email: string;
    name?: string;
  }) => void;
}

export default function Auth({ onLogin }: AuthProps) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<AuthMode>("signup");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: "",
    name: "",
    password: "",
    confirmPassword: "",
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    // Validate passwords match for signup
    if (mode === "signup" && formData.password !== formData.confirmPassword) {
      setError("Passwords do not match!");
      setLoading(false);
      return;
    }

    try {
      const { api } = await import("@/lib/api");
      const { authUtils } = await import("@/lib/auth");

      let response;

      if (mode === "signup") {
        // Register new user
        response = await api.register(
          formData.username,
          formData.name,
          formData.password,
          formData.confirmPassword
        );
      } else {
        // Login existing user
        response = await api.login(formData.username, formData.password);
      }

      // Store JWT token
      authUtils.setToken(response.tokens.access);

      // Pass user data to parent
      onLogin({
        username: response.user.username,
        email: response.user.email,
        name: response.user.name,
      });
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please try again.");
      console.error("Auth error:", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setMode(mode === "login" ? "signup" : "login");
    setFormData({ username: "", name: "", password: "", confirmPassword: "" });
    setShowPassword(false);
    setShowConfirmPassword(false);
    setError("");
  };

  return (
    <div className="min-h-screen w-full flex bg-linear-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 relative">
      <Button
        variant="ghost"
        className="absolute top-4 left-4 z-50 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 lg:text-white/80 lg:hover:text-white lg:hover:bg-white/10"
        onClick={() => navigate("/")}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Home
      </Button>

      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-center items-center p-12 relative overflow-hidden bg-[#032848]">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage:
                "radial-gradient(circle at 2px 2px, white 1px, transparent 0)",
              backgroundSize: "40px 40px",
            }}
          />
        </div>

        {/* Floating Elements */}
        <div className="absolute top-20 left-20 w-20 h-20 bg-white/10 rounded-full blur-xl" />
        <div className="absolute bottom-32 right-32 w-32 h-32 bg-violet-400/20 rounded-full blur-2xl" />
        <div className="absolute top-1/2 right-20 w-24 h-24 bg-indigo-400/20 rounded-full blur-xl" />

        {/* Content */}
        <div className="relative z-10 max-w-md space-y-8">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="h-16 w-16 rounded-2xl backdrop-blur-sm flex items-center justify-center border border-[#f4711b]">
                <ShieldCheck className="h-9 w-9 text-[#f4711b]" />
              </div>
              <div className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-emerald-400 border-2 border-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold text-[#f4711b]">QuteMail</h1>
              <p className="text-white/80 text-sm">
                Quantum Secure Communication
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-3xl font-bold text-white leading-tight">
              Secure Your Communications with Quantum Encryption
            </h2>
            <p className="text-white/90 text-lg leading-relaxed">
              Experience unbreakable security powered by Quantum Key
              Distribution (QKD) technology. Your messages are protected by the
              laws of physics.
            </p>
          </div>

          {/* Features */}
          <div className="space-y-4 pt-4">
            <div className="flex items-start gap-3">
              <div className="h-10 w-10 rounded-lg bg-white/10 flex items-center justify-center backdrop-blur-sm border border-white/20">
                <Sparkles className="h-5 w-5 text-emerald-300" />
              </div>
              <div>
                <h3 className="text-white font-semibold">
                  Quantum Key Distribution
                </h3>
                <p className="text-white/70 text-sm">
                  Unbreakable encryption using quantum mechanics
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="h-10 w-10 rounded-lg bg-white/10 flex items-center justify-center backdrop-blur-sm border border-white/20">
                <Lock className="h-5 w-5 text-blue-300" />
              </div>
              <div>
                <h3 className="text-white font-semibold">
                  End-to-End Encryption
                </h3>
                <p className="text-white/70 text-sm">
                  Your data is encrypted at all stages
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="h-10 w-10 rounded-lg bg-white/10 flex items-center justify-center backdrop-blur-sm border border-white/20">
                <ShieldCheck className="h-5 w-5 text-violet-300" />
              </div>
              <div>
                <h3 className="text-white font-semibold">
                  Future-Proof Security
                </h3>
                <p className="text-white/70 text-sm">
                  Protected against quantum computer attacks
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Auth Form */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 lg:p-12">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="h-12 w-12 rounded-xl bg-linear-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg">
              <ShieldCheck className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-linear-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">
                QuteMail
              </h1>
              <p className="text-xs text-muted-foreground">Quantum Secure</p>
            </div>
          </div>

          <Card className="border-2 shadow-xl">
            <CardHeader className="space-y-1 pb-6">
              <CardTitle className="text-2xl font-bold text-center">
                {mode === "login" ? "Welcome Back" : "Create QuteMail Account"}
              </CardTitle>
              <p className="text-sm text-muted-foreground text-center">
                {mode === "login"
                  ? "Sign in to your quantum-secure mailbox"
                  : "Get your own @qutemail.tech address with quantum encryption"}
              </p>
            </CardHeader>

            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Username Field */}
                <div className="space-y-2">
                  <label
                    htmlFor="username"
                    className="text-sm font-medium text-foreground"
                  >
                    {mode === "signup" ? "Choose Username" : "Username"}
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="username"
                      name="username"
                      type="text"
                      placeholder={
                        mode === "signup" ? "johndoe" : "Your username"
                      }
                      value={formData.username}
                      onChange={handleInputChange}
                      className="pl-10"
                      required
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                      @qutemail.tech
                    </span>
                  </div>
                  {mode === "signup" && (
                    <p className="text-xs text-muted-foreground">
                      Your email will be:{" "}
                      <span className="font-semibold text-foreground">
                        {formData.username || "username"}@qutemail.tech
                      </span>
                    </p>
                  )}
                </div>

                {/* Name Field (Signup Only) */}
                {mode === "signup" && (
                  <div className="space-y-2">
                    <label
                      htmlFor="name"
                      className="text-sm font-medium text-foreground"
                    >
                      Full Name
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="name"
                        name="name"
                        type="text"
                        placeholder="John Doe"
                        value={formData.name}
                        onChange={handleInputChange}
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>
                )}

                {/* Password Field */}
                <div className="space-y-2">
                  <label
                    htmlFor="password"
                    className="text-sm font-medium text-foreground"
                  >
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={handleInputChange}
                      className="pl-10 pr-10"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Confirm Password Field (Signup Only) */}
                {mode === "signup" && (
                  <div className="space-y-2">
                    <label
                      htmlFor="confirmPassword"
                      className="text-sm font-medium text-foreground"
                    >
                      Confirm Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="confirmPassword"
                        name="confirmPassword"
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder="••••••••"
                        value={formData.confirmPassword}
                        onChange={handleInputChange}
                        className="pl-10 pr-10"
                        required
                      />
                      <button
                        type="button"
                        onClick={() =>
                          setShowConfirmPassword(!showConfirmPassword)
                        }
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {showConfirmPassword ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {/* Forgot Password (Login Only) */}
                {mode === "login" && (
                  <div className="flex justify-end">
                    <button
                      type="button"
                      className="text-sm text-[#f4711b] hover:text-[#f4711b]/80 font-medium transition-colors"
                    >
                      Forgot password?
                    </button>
                  </div>
                )}

                {/* Error Message */}
                {error && (
                  <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                    <p className="text-sm text-red-600 dark:text-red-400">
                      {error}
                    </p>
                  </div>
                )}

                {/* Submit Button */}
                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-linear-to-r from-[#f4711b] to-orange-600 hover:from-[#f4711b]/90 hover:to-orange-600/90 text-white shadow-lg shadow-orange-500/25 transition-all duration-300 hover:shadow-xl hover:shadow-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
                  size="lg"
                >
                  {loading
                    ? "Please wait..."
                    : mode === "login"
                    ? "Sign In"
                    : "Create My QuteMail Account"}
                  {!loading && <ArrowRight className="ml-2 h-4 w-4" />}
                </Button>
              </form>

              {/* Toggle Mode */}
              <div className="mt-6 text-center">
                <p className="text-sm text-muted-foreground">
                  {mode === "login"
                    ? "Don't have a QuteMail account?"
                    : "Already have a QuteMail account?"}{" "}
                  <button
                    type="button"
                    onClick={toggleMode}
                    className="text-[#f4711b] hover:text-[#f4711b]/80 font-semibold transition-colors"
                  >
                    {mode === "login" ? "Create one" : "Sign in"}
                  </button>
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Security Badge */}
          <div className="mt-6 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800">
              <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-xs font-medium text-emerald-700 dark:text-emerald-300">
                Protected by Quantum Key Distribution
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
