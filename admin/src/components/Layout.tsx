import { Outlet } from 'react-router-dom'
import { Navbar } from './Navbar'

export default function Layout() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-7xl mx-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
