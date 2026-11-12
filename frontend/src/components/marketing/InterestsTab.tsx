/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Loader2, Tag } from 'lucide-react'
import {
  getInterestCategories,
  createInterestCategory,
  type InterestCategoryCreate,
} from '@/api/marketing-api'
import { useTranslation } from '@/i18n'
import toast from 'react-hot-toast'

export function InterestsTab({ token }: { token: string }): React.ReactElement {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState<InterestCategoryCreate>({
    name: '',
    slug: '',
    description: '',
    icon: '',
    color: '',
  })

  const { data: interests = [], isLoading } = useQuery({
    queryKey: ['interest-categories'],
    queryFn: () => getInterestCategories(),
  })

  const createMutation = useMutation({
    mutationFn: (data: InterestCategoryCreate) => createInterestCategory(token, data),
    onSuccess: () => {
      toast.success(t('marketingCampaigns.interestCategoryCreatedSuccessfully'))
      queryClient.invalidateQueries({ queryKey: ['interest-categories'] })
      setShowForm(false)
      setFormData({ name: '', slug: '', description: '', icon: '', color: '' })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '')
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Manage interest categories for subscriber segmentation
        </p>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add Category
        </button>
      </div>

      {showForm && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">New Interest Category</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => {
                    setFormData((prev) => ({
                      ...prev,
                      name: e.target.value,
                      slug: generateSlug(e.target.value),
                    }))
                  }}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  placeholder={t('placeholder.marketingCampaigns.fiction')}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Slug *
                </label>
                <input
                  type="text"
                  required
                  value={formData.slug}
                  onChange={(e) => setFormData((prev) => ({ ...prev, slug: e.target.value }))}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  placeholder={t('placeholder.marketingCampaigns.fiction1')}
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Description
              </label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                placeholder={t('marketingCampaigns.novelsShortStoriesAndLiterary')}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Icon (emoji or icon name)
                </label>
                <input
                  type="text"
                  value={formData.icon}
                  onChange={(e) => setFormData((prev) => ({ ...prev, icon: e.target.value }))}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  placeholder={t('placeholder.marketingCampaigns.book')}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Color (hex)
                </label>
                <input
                  type="text"
                  value={formData.color}
                  onChange={(e) => setFormData((prev) => ({ ...prev, color: e.target.value }))}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  placeholder={t('placeholder.marketingCampaigns.3b82f6')}
                />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl transition-colors flex items-center gap-2"
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Category'
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : interests.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center">
          <Tag className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('marketingCampaigns.noInterestCategoriesYet')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {interests.map((interest) => (
            <div
              key={interest.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    {interest.icon && <span className="text-lg">{interest.icon}</span>}
                    <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">{interest.name}</h4>
                  </div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    {interest.description || 'No description'}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    Slug: {interest.slug}
                  </p>
                </div>
                {interest.color && (
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: interest.color }}
                  />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
