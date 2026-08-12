"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

// Mirrors the backend's RegisterRequest pseudo pattern (backend/app/api/v1/schemas/auth.py):
// no whitespace, no '@', 3-50 chars.
const PSEUDO_PATTERN = /^[^\s@]{3,50}$/;

function isValidDateOfBirth(value: string): boolean {
  const parsed = new Date(value + "T00:00:00Z");
  if (Number.isNaN(parsed.getTime())) return false;
  const today = new Date();
  if (parsed.getTime() > today.getTime()) return false;
  const ageYears = (today.getTime() - parsed.getTime()) / (365.25 * 24 * 60 * 60 * 1000);
  return ageYears >= 3 && ageYears <= 120;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [firstname, setFirstname] = useState("");
  const [lastname, setLastname] = useState("");
  const [email, setEmail] = useState("");
  const [pseudo, setPseudo] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const pseudoValid = pseudo.length === 0 || PSEUDO_PATTERN.test(pseudo.trim());
  const dateOfBirthValid = dateOfBirth.length === 0 || isValidDateOfBirth(dateOfBirth);
  const passwordsMatch = confirmPassword.length === 0 || password === confirmPassword;

  const canSubmit =
    !!firstname && !!lastname && !!email && !!pseudo && !!dateOfBirth && password.length > 0 && !!confirmPassword;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!PSEUDO_PATTERN.test(pseudo.trim())) {
      setError("Username must be 3-50 characters, no spaces or '@'.");
      return;
    }
    if (!isValidDateOfBirth(dateOfBirth)) {
      setError("Enter a valid date of birth.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    setIsSubmitting(true);
    try {
      await register({
        email: email.trim(),
        password,
        confirm_password: confirmPassword,
        firstname: firstname.trim(),
        lastname: lastname.trim(),
        pseudo: pseudo.trim(),
        date_of_birth: dateOfBirth,
      });
      router.replace("/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create your account. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">Create your account</CardTitle>
        <CardDescription>Start studying smarter with AI-generated help.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex gap-3">
            <div className="flex flex-1 flex-col gap-2">
              <Label htmlFor="firstname">First name</Label>
              <Input id="firstname" value={firstname} onChange={(e) => setFirstname(e.target.value)} required />
            </div>
            <div className="flex flex-1 flex-col gap-2">
              <Label htmlFor="lastname">Last name</Label>
              <Input id="lastname" value={lastname} onChange={(e) => setLastname(e.target.value)} required />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="pseudo">Username</Label>
            <Input
              id="pseudo"
              autoComplete="username"
              value={pseudo}
              onChange={(e) => setPseudo(e.target.value)}
              required
            />
            {!pseudoValid ? (
              <p className="text-xs text-destructive">3-50 characters, no spaces or &apos;@&apos;.</p>
            ) : null}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="dob">Date of birth</Label>
            <Input
              id="dob"
              type="date"
              value={dateOfBirth}
              onChange={(e) => setDateOfBirth(e.target.value)}
              required
            />
            {!dateOfBirthValid ? <p className="text-xs text-destructive">Enter a valid date of birth.</p> : null}
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <p className="text-xs text-muted-foreground">At least 8 characters.</p>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="confirmPassword">Confirm password</Label>
            <Input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
            {!passwordsMatch ? <p className="text-xs text-destructive">Passwords don&apos;t match.</p> : null}
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" disabled={isSubmitting || !canSubmit} className="mt-2">
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
          <div className="flex justify-center text-sm text-muted-foreground">
            <Link href="/login" className="hover:text-foreground hover:underline">
              Already have an account? Sign in
            </Link>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
