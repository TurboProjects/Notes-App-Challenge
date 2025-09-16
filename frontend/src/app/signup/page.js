"use client"

import Image from 'next/image'
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

// CatIllustration component
const CatIllustration = () => (
  <div className="mb-8 flex justify-center">
    <Image
      src="cat.png"
      alt="Cute sleeping cat illustration"
      width={192}
      height={192}
      className="w-48 h-auto"
      unoptimized
    />
  </div>
)

// EmailInput component
const EmailInput = ({ field }) => (
  <FormItem>
    <FormLabel htmlFor="email" className="text-[#895f38]">Email address</FormLabel>
    <FormControl>
      <Input
        {...field}
        id="email"
        type="email"
        placeholder="Enter your email"
        className="w-full px-4 py-2 rounded-md border border-[#955f38] bg-transparent text-[#895f38] placeholder-[#895f38] focus:outline-none focus:ring-2 focus:ring-[#955f38]"
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
      <FormLabel htmlFor="password" className="text-[#895f38]">Password</FormLabel>
      <FormControl>
        <div className="relative">
          <Input
            {...field}
            id="password"
            type={showPassword ? "text" : "password"}
            placeholder="Enter your password"
            className="w-full px-4 py-2 rounded-md border border-[#955f38] bg-transparent text-[#895f38] placeholder-[#895f38] focus:outline-none focus:ring-2 focus:ring-[#955f38]"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-2 top-1/2 -translate-y-1/2"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4 text-[#895f38]" />
            ) : (
              <Eye className="h-4 w-4 text-[#895f38]" />
            )}
          </Button>
        </div>
      </FormControl>
      <FormMessage />
    </FormItem>
  )
}

// SignupButton component
const SignupButton = () => (
  <Button
    type="submit"
    className="w-full px-4 py-2 rounded-full bg-transparent border border-[#955f38] text-[#895f38] font-bold hover:bg-[#955f38] hover:text-white transition-colors"
  >
    Sign Up
  </Button>
)

// LoginLink component
const LoginLink = () => (
  <div className="mt-4 text-center">
    <a href="login" className="text-sm text-[#895f38] underline">
      We&apos;re already friends!
    </a>
  </div>
)

// Main SignupForm component
const SignupForm = () => {
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
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/register/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (response.status === 201) {
        const resData = await response.json()
        await loginWithToken(resData.user.auth_token);
        router.push('/notes')
      } else if (response.status === 400) {
        const result = await response.json()
        Object.keys(result.errors).forEach((field) => {
          form.setError(field, { type: 'server', message: result.errors[field][0] })
        })
      } else {
        setGenericError('An unexpected error occurred. Please try again.')
      }
    } catch (error) {
      setGenericError('Network error. Please check your connection and try again.')
    }
  }

  return (
    <div className="bg-[#faf1e4] flex items-center justify-center min-h-screen">
      <div className="max-w-md w-full px-4 py-8 sm:px-6 lg:px-8">
        <CatIllustration />
        <h1 className="text-4xl font-bold text-[#895f38] text-center mb-8">
          Yay, New Friend!
        </h1>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {genericError && (
              <div className="text-red-500 text-center mb-4">
                {genericError}
              </div>
            )}
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
            <SignupButton />
          </form>
        </Form>
        <LoginLink />
      </div>
    </div>
  )
}

export default SignupForm