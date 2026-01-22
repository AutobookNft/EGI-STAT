import React from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    LabelList
} from 'recharts';

/**
 * AdminChart - A strict "Scientific/Admin" style chart component.
 * 
 * Rules:
 * 1. Straight lines (type="linear") - No smoothing.
 * 2. Distinct Markers (dots) - To show exact data points.
 * 3. Dynamic Scaling (domain) - To show variation (Mountain vs Flat).
 * 4. Gridlines (Carta millimetrata) - Major and minor (simulated).
 * 5. Data Labels - Explicit values on nodes.
 */
const AdminChart = ({
    data,
    dataKey,
    xAxisKey = "name",
    title,
    color = "#000000",
    yLabel = "Value",
    scrollable = false
}) => {

    // Calculate dynamic domain with padding (Admin Rule: +20% top, -10% bottom)
    const calculateDomain = (data) => {
        if (!data || data.length === 0) return [0, 'auto'];
        const values = data.map(d => d[dataKey]);
        const min = Math.min(...values);
        const max = Math.max(...values);

        if (min === max) {
            return [min > 0 ? 0 : 'auto', 'auto'];
        }

        const range = max - min;
        // Padding logic: Don't flatten the mountain
        let domainMin = Math.floor(min - (range * 0.1));
        let domainMax = Math.ceil(max + (range * 0.2));

        if (min >= 0 && domainMin < 0) domainMin = 0; // Don't go negative if data is positive

        return [domainMin, domainMax];
    };

    const domain = calculateDomain(data);

    // SQUARE GRID LOGIC ------------------------
    // Use fixed dimensions to force geometric squares.

    // 1. Vertical setup
    const CHART_HEIGHT = 400;
    const MARGIN = { top: 20, right: 30, left: 20, bottom: 20 };
    const INNER_HEIGHT = CHART_HEIGHT - MARGIN.top - MARGIN.bottom; // 360px
    const Y_TICKS = 6; // Force 5 intervals
    const Y_INTERVALS = Y_TICKS - 1;
    const GRID_SIZE = INNER_HEIGHT / Y_INTERVALS; // 72px per square side

    // 2. Horizontal setup (Force X interval to match GRID_SIZE)
    const pointsCount = data ? data.length : 0;
    const X_PADDING = 30; // Matches XAxis padding

    // Formula: The line length is (points - 1) * GRID_SIZE
    // Total Width = LineLength + (X_PADDING * 2) + MARGIN.left + MARGIN.right
    const EXACT_WIDTH = Math.max(pointsCount - 1, 0) * GRID_SIZE + (X_PADDING * 2) + MARGIN.left + MARGIN.right;

    // Ensure minimum width for very few points
    const FINAL_WIDTH = Math.max(600, EXACT_WIDTH);

    const ChartContent = (
        <LineChart
            width={FINAL_WIDTH}
            height={CHART_HEIGHT}
            data={data}
            margin={MARGIN}
        >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
            <XAxis
                dataKey={xAxisKey}
                tick={{ fontSize: 12 }}
                padding={{ left: X_PADDING, right: X_PADDING }}
                tickLine={true}
                interval={0}
            />
            <YAxis
                domain={domain}
                tickCount={Y_TICKS}
                tick={{ fontSize: 12 }}
                label={{ value: yLabel, angle: -90, position: 'insideLeft' }}
            />
            <Tooltip
                contentStyle={{ borderRadius: '0px', border: '1px solid black' }}
                itemStyle={{ color: 'black', fontWeight: 'bold' }}
            />
            <Line
                type="linear"
                dataKey={dataKey}
                stroke={color}
                strokeWidth={2}
                dot={{ r: 4, fill: "white", stroke: color, strokeWidth: 2 }}
                activeDot={{ r: 6, fill: color, stroke: "white" }}
                isAnimationActive={false}
            >
                <LabelList position="top" offset={10} fontSize={10} />
            </Line>
        </LineChart>
    );

    return (
        <div style={{ width: '100%', background: 'rgba(255,255,255,0.9)', padding: '10px', borderRadius: '8px', overflowX: 'auto' }}>
            {title && (
                <div style={{ textAlign: 'center', fontWeight: 'bold', marginBottom: '10px', textTransform: 'uppercase' }}>
                    {title}
                </div>
            )}

            <div style={{ width: `${FINAL_WIDTH}px`, height: `${CHART_HEIGHT}px` }}>
                {ChartContent}
            </div>
        </div>
    );
};

export default AdminChart;
