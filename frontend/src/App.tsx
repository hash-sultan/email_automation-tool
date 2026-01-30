import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/Layout'
import { SkeletonCard } from './components/SkeletonLoader'

// Lazy load pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Campaigns = lazy(() => import('./pages/Campaigns'))
const Leads = lazy(() => import('./pages/Leads'))
const Senders = lazy(() => import('./pages/Senders'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Settings = lazy(() => import('./pages/Settings'))
const Replies = lazy(() => import('./pages/Replies'))
// Template routes
const TemplatesIndex = lazy(() => import('./pages/templates/TemplatesIndex'))
const TemplatesCategoryList = lazy(() => import('./pages/templates/TemplatesCategoryList'))
const TemplatesCategoryView = lazy(() => import('./pages/templates/TemplatesCategoryView'))
const TemplateForm = lazy(() => import('./pages/templates/TemplateForm'))

function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1f2937',
            color: '#f3f4f6',
            border: '1px solid #374151',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#1f2937',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#1f2937',
            },
          },
        }}
      />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route 
            index 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <Dashboard />
              </Suspense>
            } 
          />
          <Route 
            path="campaigns" 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <Campaigns />
              </Suspense>
            } 
          />
          <Route 
            path="campaigns/new" 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <Campaigns />
              </Suspense>
            } 
          />
          <Route 
            path="campaigns/:campaignId" 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <Campaigns />
              </Suspense>
            } 
          />
          <Route 
            path="leads" 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <Leads />
              </Suspense>
            } 
          />
          <Route 
            path="templates" 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <TemplatesIndex />
              </Suspense>
            }
          >
            <Route 
              index 
              element={
                <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                  <TemplatesCategoryList />
                </Suspense>
              } 
            />
            <Route 
              path="categories/new" 
              element={
                <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                  <TemplateForm />
                </Suspense>
              } 
            />
            <Route 
              path="categories/:categoryId" 
              element={
                <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                  <TemplatesCategoryView />
                </Suspense>
              } 
            />
            <Route 
              path="categories/:categoryId/new" 
              element={
                <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                  <TemplateForm />
                </Suspense>
              } 
            />
            <Route 
              path="categories/:categoryId/:templateId/edit" 
              element={
                <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                  <TemplateForm />
                </Suspense>
              } 
            />
          </Route>
          <Route 
            path="senders" 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <Senders />
              </Suspense>
            } 
          />
          <Route 
            path="replies" 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <Replies />
              </Suspense>
            } 
          />
          <Route 
            path="analytics" 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <Analytics />
              </Suspense>
            } 
          />
          <Route 
            path="settings" 
            element={
              <Suspense fallback={<div className="p-6"><SkeletonCard /></div>}>
                <Settings />
              </Suspense>
            } 
          />
        </Route>
      </Routes>
    </>
  )
}

export default App

