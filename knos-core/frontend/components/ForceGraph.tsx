// components/ForceGraph.tsx
"use client"
import { useEffect, useRef, useCallback } from "react"
import * as d3 from "d3"
import type { GraphData } from "@/lib/api"
import { TYPE_META } from "@/lib/utils"

interface Props {
  data: GraphData
  onNodeClick?: (nodeId: string) => void
  width?: number
  height?: number
}

const TYPE_COLORS: Record<string, string> = {
  webpage:    "#3b82f6",
  thought:    "#8b5cf6",
  book:       "#f59e0b",
  video:      "#ef4444",
  document:   "#6b7280",
  media:      "#ec4899",
  person:     "#22c55e",
  org:        "#14b8a6",
  place:      "#f97316",
  event:      "#06b6d4",
  definition: "#6366f1",
  liked:      "#f43f5e",
  ai_conv:    "#0ea5e9",
}

interface D3Node extends d3.SimulationNodeDatum {
  id: string
  title: string
  type: string
}

interface D3Link extends d3.SimulationLinkDatum<D3Node> {
  id: string
  type: string
  strength: number
}

export function ForceGraph({ data, onNodeClick, width = 800, height = 600 }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  const render = useCallback(() => {
    const svg = d3.select(svgRef.current!)
    svg.selectAll("*").remove()

    const nodes: D3Node[] = data.nodes.map(n => ({ ...n }))
    const links: D3Link[] = data.edges.map(e => ({
      ...e,
      source: e.source,
      target: e.target,
    }))

    const simulation = d3.forceSimulation<D3Node>(nodes)
      .force("link", d3.forceLink<D3Node, D3Link>(links).id(d => d.id).distance(d => 100 / (d.strength || 1)))
      .force("charge", d3.forceManyBody().strength(-220))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide(28))

    // Zoom
    const g = svg.append("g")
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 6])
        .on("zoom", e => g.attr("transform", e.transform))
    )

    // Links
    const link = g.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#3d3834")
      .attr("stroke-width", d => 0.5 + d.strength * 2)
      .attr("stroke-opacity", 0.7)

    // Node groups
    const nodeG = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .call(
        d3.drag<SVGGElement, D3Node>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x; d.fy = d.y
          })
          .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null; d.fy = null
          })
      )
      .on("click", (_, d) => onNodeClick?.(d.id))
      .on("mouseover", (event, d) => {
        if (!tooltipRef.current) return
        tooltipRef.current.style.display = "block"
        tooltipRef.current.style.left = `${event.pageX + 12}px`
        tooltipRef.current.style.top  = `${event.pageY - 8}px`
        tooltipRef.current.innerHTML  = `<strong>${d.title}</strong><br/><span style="font-size:11px;opacity:.7">${d.type}</span>`
      })
      .on("mouseout", () => {
        if (tooltipRef.current) tooltipRef.current.style.display = "none"
      })

    // Node circles
    nodeG.append("circle")
      .attr("r", 14)
      .attr("fill", d => (TYPE_COLORS[d.type] || "#6b7280") + "33")
      .attr("stroke", d => TYPE_COLORS[d.type] || "#6b7280")
      .attr("stroke-width", 1.5)

    // Node icons
    nodeG.append("text")
      .text(d => TYPE_META[d.type as keyof typeof TYPE_META]?.icon || "⬡")
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "central")
      .attr("font-size", 13)
      .style("user-select", "none")
      .style("pointer-events", "none")

    // Labels
    nodeG.append("text")
      .text(d => d.title.slice(0, 18) + (d.title.length > 18 ? "…" : ""))
      .attr("text-anchor", "middle")
      .attr("dy", 24)
      .attr("font-size", 10)
      .attr("fill", "#9d948b")
      .style("user-select", "none")
      .style("pointer-events", "none")

    simulation.on("tick", () => {
      link
        .attr("x1", d => (d.source as D3Node).x!)
        .attr("y1", d => (d.source as D3Node).y!)
        .attr("x2", d => (d.target as D3Node).x!)
        .attr("y2", d => (d.target as D3Node).y!)

      nodeG.attr("transform", d => `translate(${d.x},${d.y})`)
    })

    return () => simulation.stop()
  }, [data, width, height, onNodeClick])

  useEffect(() => {
    const cleanup = render()
    return cleanup
  }, [render])

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        style={{ width: "100%", height: "100%" }}
      />
      <div
        ref={tooltipRef}
        className="graph-tooltip"
        style={{ display: "none" }}
      />
    </div>
  )
}
