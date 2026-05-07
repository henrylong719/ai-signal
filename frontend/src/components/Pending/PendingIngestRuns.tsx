import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

/**
 * Loading skeleton for the ingest-runs table.
 *
 * Mirrors the column structure of ingestRunColumns so the layout
 * doesn't reflow when real data arrives. Five rows is the same count
 * as PendingUsers — enough to fill the visual area without looking
 * like meaningful pagination.
 */
const PendingIngestRuns = () => (
  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>Started</TableHead>
        <TableHead>Status</TableHead>
        <TableHead>Duration</TableHead>
        <TableHead>Inserted</TableHead>
        <TableHead>Skipped</TableHead>
        <TableHead>Embedded</TableHead>
        <TableHead>Errors</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {Array.from({ length: 5 }).map((_, index) => (
        <TableRow key={index}>
          <TableCell>
            <Skeleton className="h-4 w-32" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-5 w-24 rounded-full" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-12" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-8" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-8" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-8" />
          </TableCell>
          <TableCell>
            <Skeleton className="h-4 w-32" />
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
)

export default PendingIngestRuns
