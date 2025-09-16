"use client"

import Image from 'next/image'
import Link from 'next/link'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Eye, EyeOff } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useAuth } from "@/context/AuthProvider"

// Define the form schema for validation
const formSchema = z.object({
  email: z.string().email({ message: "Invalid email address" }),
  password: z.string().min(8, { message: "Password must be at least 8 characters" })
})

// CactusIllustration component
const CactusIllustration = () => (
  <div className="mb-6 flex justify-center">
    <Image
      src="cactus.png"
      alt="Cute cactus illustration"
      width={96}
      height={112}
      className="w-24 h-28"
      unoptimized
    />
  </div>
)

// EmailInput component
const EmailInput = ({ field }) => (
  <FormItem>
    <FormLabel htmlFor="email" className="text-[#885f37]">Email address</FormLabel>
    <FormControl>
      <Input
        {...field}
        id="email"
        type="email"
        placeholder="Email address"
        className="w-full px-4 py-2 rounded-md border border-[#95714f] bg-transparent text-[#000000] placeholder-[#95714f] focus:outline-none focus:ring-2 focus:ring-[#95714f]"
      />
    </FormControl>
    <FormMessage />
  </FormItem>
)

// PasswordInput component
const PasswordInput = ({ field }) => {
  const [showPassword, setShowPassword] = useState(false)

  return (
    <FormItem>
      <FormLabel htmlFor="password" className="text-[#885f37]">Password</FormLabel>
      <FormControl>
        <div className="relative">
          <Input
            {...field}
            id="password"
            type={showPassword ? "text" : "password"}
            placeholder="Password"
            className="w-full px-4 py-2 rounded-md border border-[#95714f] bg-transparent text-[#000000] placeholder-[#95714f] focus:outline-none focus:ring-2 focus:ring-[#95714f]"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-2 top-1/2 -translate-y-1/2"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4 text-[#95714f]" />
            ) : (
              <Eye className="h-4 w-4 text-[#95714f]" />
            )}
          </Button>
        </div>
      </FormControl>
      <FormMessage />
    </FormItem>
  )
}

// LoginButton component
const LoginButton = () => (
  <Button
    type="submit"
    className="w-full py-3 px-4 bg-transparent border border-[#95714f] rounded-full text-[#95714f] font-bold hover:bg-[#95714f] hover:text-white transition-colors"
  >
    Login
  </Button>
)

// SignupLink component
const SignupLink = () => (
  <div className="mt-4 text-center">
    <Link href="/signup" className="text-sm text-[#95714f] underline">
      Oops! I&apos;ve never been here before
    </Link>
  </div>
)

// Main LoginForm component
const LoginForm = () => {
  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      password: ""
    }
  })
  const router = useRouter()
  const [genericError, setGenericError] = useState('')
  const { loginWithToken } = useAuth()

  const onSubmit = async (data) => {
    setGenericError('')
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth-token/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: data.email,
          password: data.password,
        }),
      })
      if (response.ok) {
        const resData = await response.json()
        await loginWithToken(resData.token);
        router.push('/notes')
      } else {
        const errorData = await response.json()
        setGenericError(errorData.non_field_errors || 'Invalid credentials')
      }
    } catch (error) {
      setGenericError('Network error. Please try again later.')
    }
  }

  return (
    <div className="bg-[#faf1e4] flex items-center justify-center min-h-screen">
      <div className="max-w-md w-full px-4 py-8 sm:px-6 lg:px-8">
        <CactusIllustration />
        <h1 className="text-4xl font-bold text-[#885f37] text-center mb-8">
          Yay, You&apos;re Back!
        </h1>
        {genericError && (
          <div className="text-red-500 text-center mb-4">
            {genericError}
          </div>
        )}
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => <EmailInput field={field} />}
            />
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => <PasswordInput field={field} />}
            />
            <LoginButton />
          </form>
        </Form>
        <SignupLink />
      </div>
    </div>
  )
}

export default LoginForm