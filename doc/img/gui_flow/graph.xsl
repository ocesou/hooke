<?xml version="1.0" encoding="utf-8" standalone="no"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:svg="http://www.w3.org/2000/svg"
		xmlns:xlink="http://www.w3.org/1999/xlink"
                xmlns:math="http://exslt.org/math"
		xmlns:ex="http://www.example.com/graph"
                version="1.0">
  <xsl:import href="math.sqrt.template.xsl"/>
  <xsl:output indent="yes"/>

  <xsl:template match="ex:graph">
    <xsl:variable name="view-box" select="./ex:config/@viewBox"/>
    <svg:svg version="1.0" viewBox="{$view-box}">
      <svg:defs>
	<xsl:variable name="arc-color" select="./ex:config/@arc-color"/>
	<svg:marker id="arrowhead" viewBox="0 0 20 20" refX="20" refY="10" 
		    markerUnits="strokeWidth" markerWidth="8" markerHeight="6"
		    orient="auto" style="{$arc-color}">
	  <svg:path d="M 0 0 L 20 10 L 0 20 z"/>
	</svg:marker>
      </svg:defs>
      <!-- making sure the arcs are drawn first -->
      <xsl:apply-templates select="ex:arc"/>
      <xsl:apply-templates select="ex:node"/>
    </svg:svg>
  </xsl:template>

  <xsl:template match="ex:arc">
    <xsl:variable name="text-color" select="../ex:config/@text-color"/>
    <xsl:variable name="arc-color" select="../ex:config/@arc-color"/>
    <xsl:variable name="node-radius" select="../ex:config/@node-radius"/>
    <xsl:variable name="arc-offset" select="../ex:config/@arc-offset"/>
    <svg:g style="{$arc-color}">
      <xsl:variable name="from"><xsl:value-of select="@from"/></xsl:variable>
      <xsl:variable name="to"><xsl:value-of select="@to"/></xsl:variable>
      <xsl:variable name="x1" select="../ex:node[@name=$from]/@cx"/>
      <xsl:variable name="y1" select="../ex:node[@name=$from]/@cy"/>
      <xsl:variable name="x2" select="../ex:node[@name=$to]/@cx"/>
      <xsl:variable name="y2" select="../ex:node[@name=$to]/@cy"/>
      <!-- calculate endpoints shortened by $node-radius + $arc-offset -->
      <xsl:variable name="Dx" select="$x2 - $x1"/>
      <xsl:variable name="Dy" select="$y2 - $y1"/>
      <xsl:variable name="Dsquare" select="($Dx*$Dx + $Dy*$Dy)"/>
      <xsl:variable name="D"><xsl:call-template name="sqrt">
	  <xsl:with-param name="number" select="$Dsquare"/>
      </xsl:call-template></xsl:variable>
      <xsl:variable name="a-off" select="$node-radius + $arc-offset"/> 
      <xsl:variable name="dx" select="$a-off * $Dx div $D"/>
      <xsl:variable name="dy" select="$a-off * $Dy div $D"/>
      <xsl:variable name="X1" select="$x1 + $dx"/>
      <xsl:variable name="Y1" select="$y1 + $dy"/>
      <xsl:variable name="X2" select="$x2 - $dx"/>
      <xsl:variable name="Y2" select="$y2 - $dy"/>
      <svg:path style="marker-end:url(#arrowhead);stroke-width:1;"
		d="M{$X1} {$Y1} L{$X2} {$Y2}"/>
      <svg:defs>
	<svg:path id="textPath-{@label}" d="M{$X1} {$Y1} L{$X2} {$Y2}"/>
      </svg:defs>
      <svg:text text-anchor="middle" style="{$text-color}">
	<svg:textPath xlink:href="#textPath-{@label}" startOffset="50%">
	  <svg:tspan dy="-0.4em">  <!-- raise text slightly off the line -->
	    <xsl:value-of select="@label"/>
	  </svg:tspan>
	</svg:textPath>
      </svg:text>
    </svg:g>
  </xsl:template>

  <xsl:template match="ex:node">
    <xsl:variable name="text-color" select="../ex:config/@text-color"/>
    <xsl:variable name="node-color" select="../ex:config/@node-color"/>
    <xsl:variable name="node-radius" select="../ex:config/@node-radius"/>
    <svg:g style="{$node-color}">
      <svg:circle cx="{@cx}" cy="{@cy}" r="{$node-radius}"/>
      <svg:text text-anchor="middle" x="{@cx}" y="{@cy}"
		style="dominant-baseline:central;{$text-color}">
	<xsl:value-of select="@label"/>
      </svg:text>
    </svg:g>
  </xsl:template>
</xsl:stylesheet>
