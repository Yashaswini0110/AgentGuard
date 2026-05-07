import AppShell from '@/components/AppShell'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ReviewQueueInner } from './ReviewQueuePage'
import { TechReviewInner } from './TechReviewPage'

export default function IncidentQueuePage() {
  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="font-sans font-semibold" style={{ fontSize: '22px', color: '#0D0D0D' }}>
          Incident queue
        </h1>
        <p className="font-sans text-sm mt-1" style={{ color: '#6B6B6B' }}>
          Human oversight and technical review lanes for RED / elevated decisions.
        </p>
      </div>
      <Tabs defaultValue="oversight">
        <TabsList>
          <TabsTrigger value="oversight">Compliance oversight</TabsTrigger>
          <TabsTrigger value="technical">Technical review</TabsTrigger>
        </TabsList>
        <TabsContent value="oversight" className="mt-6">
          <ReviewQueueInner embedded />
        </TabsContent>
        <TabsContent value="technical" className="mt-6">
          <TechReviewInner embedded />
        </TabsContent>
      </Tabs>
    </AppShell>
  )
}
